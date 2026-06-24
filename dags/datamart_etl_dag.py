from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/opt/airflow/scripts")

from extract import extract_source_1, extract_source_2
from transform import transform
from load import load, create_tables
from load import load

default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="datamart_etl",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
) as dag:

    t_extract_1 = PythonOperator(
        task_id="extract_source_1",
        python_callable=extract_source_1,
    )

    t_extract_2 = PythonOperator(
        task_id="extract_source_2",
        python_callable=extract_source_2,
    )

    t_transform = PythonOperator(
        task_id="transform",
        python_callable=transform,
    )

    t_create_tables = PythonOperator(
    task_id="create_tables",
    python_callable=create_tables,
    )

    t_load = PythonOperator(
        task_id="load",
        python_callable=load,
    )

    [t_extract_1, t_extract_2] >> t_transform >>  t_create_tables >> t_load