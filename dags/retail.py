from airflow.decorators import dag, task
from airflow.operators.python import ExternalPythonOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from datetime import datetime
import os

# Path to the isolated Python venv created in Dockerfile
ISOLATED_PYTHON = "/usr/local/airflow/dbt_cosmos_env/bin/python"

# Schema definition for raw_invoices table
schema_fields = [
    {"name": "InvoiceNo", "type": "STRING", "mode": "NULLABLE"},
    {"name": "StockCode", "type": "STRING", "mode": "NULLABLE"},
    {"name": "Description", "type": "STRING", "mode": "NULLABLE"},
    {"name": "Quantity", "type": "INTEGER", "mode": "NULLABLE"},
    {"name": "InvoiceDate", "type": "STRING", "mode": "NULLABLE"},
    {"name": "UnitPrice", "type": "FLOAT", "mode": "NULLABLE"},
    {"name": "CustomerID", "type": "STRING", "mode": "NULLABLE"},
    {"name": "Country", "type": "STRING", "mode": "NULLABLE"},
]

@dag(
    start_date=datetime(2023, 1, 1),
    schedule=None,
    catchup=False,
    tags=['retail'],
)
def retail():
    upload_csv_to_gcs = LocalFilesystemToGCSOperator(
        task_id='upload_csv_to_gcs',
        src='include/dataset/online_retail.csv',
        dst='raw/online_retail.csv',
        bucket='ashleyesau_online_retail',
        gcp_conn_id='gcp',
        mime_type='text/csv',
    )

    create_retail_dataset = BigQueryCreateEmptyDatasetOperator(
        task_id='create_retail_dataset',
        dataset_id='retail',
        gcp_conn_id='gcp',
    )

    gcs_to_raw = GCSToBigQueryOperator(
        task_id='gcs_to_raw',
        bucket='ashleyesau_online_retail',
        source_objects=['raw/online_retail.csv'],
        destination_project_dataset_table='retail.raw_invoices',
        source_format='CSV',
        gcp_conn_id='gcp',
        schema_fields=schema_fields,
        create_disposition='CREATE_IF_NEEDED',
        write_disposition='WRITE_TRUNCATE',
        skip_leading_rows=1,
        autodetect=False,
    )

    @task
    def check_load(scan_name='check_load', checks_subpath='sources'):
        from include.soda.check_function import check
        return check(scan_name, checks_subpath)

    check_load_task = check_load()

    # --------- dbt transform ----------
    def run_dbt_transform():
        import subprocess
        project_dir = "/usr/local/airflow/dbt"
        profiles_dir = "/usr/local/airflow/dbt"
        subprocess.run(
            [
                "dbt", "run",
                "--select", "path:models/transform",
                "--project-dir", project_dir,
                "--profiles-dir", profiles_dir,
                "--full-refresh"
            ],
            check=True
        )

    transform = ExternalPythonOperator(
        task_id="transform",
        python=ISOLATED_PYTHON,
        python_callable=run_dbt_transform
    )

    @task
    def check_transform(scan_name='check_transform', checks_subpath='transform'):
        from include.soda.check_function import check
        return check(scan_name, checks_subpath)

    check_transform_task = check_transform()

    # --------- dbt report ----------
    def run_dbt_report():
        import subprocess
        project_dir = "/usr/local/airflow/dbt"
        profiles_dir = "/usr/local/airflow/dbt"
        subprocess.run(
            [
                "dbt", "run",
                "--select", "path:models/report",
                "--project-dir", project_dir,
                "--profiles-dir", profiles_dir,
                "--full-refresh"
            ],
            check=True
        )

    report = ExternalPythonOperator(
        task_id="report",
        python=ISOLATED_PYTHON,
        python_callable=run_dbt_report
    )

    @task
    def check_report(scan_name='check_report', checks_subpath='report'):
        from include.soda.check_function import check
        return check(scan_name, checks_subpath)

    check_report_task = check_report()

    (
        upload_csv_to_gcs
        >> create_retail_dataset
        >> gcs_to_raw
        >> check_load_task
        >> transform
        >> check_transform_task
        >> report
        >> check_report_task
    )

retail()