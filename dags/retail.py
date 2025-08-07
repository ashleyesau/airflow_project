from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator
from datetime import datetime
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
import os
from pathlib import Path

# DEBUG: Check file system access
print("=" * 50)
print("DEBUG: File system check")
print(f"Current working directory: {os.getcwd()}")
print(f"/usr/local/airflow exists: {os.path.exists('/usr/local/airflow')}")
print(f"/usr/local/airflow/dbt exists: {os.path.exists('/usr/local/airflow/dbt')}")
print(f"/usr/local/airflow/dbt/dbt_project.yml exists: {os.path.exists('/usr/local/airflow/dbt/dbt_project.yml')}")
print(f"/usr/local/airflow/dbt/target exists: {os.path.exists('/usr/local/airflow/dbt/target')}")
print(f"/usr/local/airflow/dbt/target/manifest.json exists: {os.path.exists('/usr/local/airflow/dbt/target/manifest.json')}")
if os.path.exists('/usr/local/airflow'):
    print(f"Contents of /usr/local/airflow: {os.listdir('/usr/local/airflow')}")
if os.path.exists('/usr/local/airflow/dbt'):
    print(f"Contents of /usr/local/airflow/dbt: {os.listdir('/usr/local/airflow/dbt')}")
if os.path.exists('/usr/local/airflow/dbt/target'):
    print(f"Contents of /usr/local/airflow/dbt/target: {os.listdir('/usr/local/airflow/dbt/target')}")
print("=" * 50)

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

    from cosmos.airflow.task_group import DbtTaskGroup
    from cosmos.config import ProjectConfig, RenderConfig
    from cosmos.constants import LoadMode
    from dbt.cosmos_config import DBT_CONFIG  

    project_dir = "/usr/local/airflow/dbt"
    manifest_path = str(Path(project_dir) / "target" / "manifest.json")

    transform = DbtTaskGroup(
        group_id='transform',
        project_config=ProjectConfig(
            dbt_project_path=project_dir,
            manifest_path=manifest_path,
        ),
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST,  
        ),
        operator_args={
            "install_deps": False,
            "full_refresh": True,
        },
    )

    @task
    def check_transform(scan_name='check_transform', checks_subpath='transform'):
        from include.soda.check_function import check
        return check(scan_name, checks_subpath)
    
    check_transform_task = check_transform()

    report = DbtTaskGroup(
        group_id='report',
        project_config=ProjectConfig(
            dbt_project_path=project_dir,
            manifest_path=manifest_path,
        ),
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST,
            select=['path:models/report'],
        ),
        operator_args={
            "install_deps": False,
            "full_refresh": True,
        },
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
