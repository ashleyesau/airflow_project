from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

# Simple DAG definition - no decorators, no complex imports
dag = DAG(
    'simple_test',
    start_date=datetime(2023, 1, 1),
    schedule=None,  # Changed from schedule_interval to schedule
    catchup=False,
    tags=['test']
)

# Just test basic file access
test_task = BashOperator(
    task_id='test_basic_access',
    bash_command='''
    echo "=== Basic File Test ==="
    pwd
    ls -la /usr/local/airflow/ || echo "/usr/local/airflow not found"
    ls -la /usr/local/airflow/dbt/ || echo "dbt dir not found"  
    ls -la dbt/ || echo "relative dbt dir not found"
    echo "=== End Test ==="
    ''',
    dag=dag
)