from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from includes.parse_data import process_data
from includes.train import train_model

TRAIN_DATA_PATH = "data/droughtwatch_data/train"
VAL_DATA_PATH = "data/droughtwatch_data/val"


def process_raw_data():
    process_data(TRAIN_DATA_PATH)
    process_data(VAL_DATA_PATH)


def create_data_process_task(task_id=None):
    return PythonOperator(task_id=task_id, python_callable=process_raw_data)


def train_baseline():
    """
    Train the baseline model with default configs
    """
    train_model()


def train_dummy():
    """
    Train a dummy model, i.e. just return the untrained model
    """
    train_model(model_config="dummy")


def train_useful():
    """
    Train the baseline model for more epochs to get better predictions
    """
    train_model(model_config="useful")


def train_ndvi():
    """
    Train the baseline model on NDVI as the only feature.
    Useful as NDVI is supposed to be a good measure of vegetation.
    """
    train_model(override_args={"training.features.list": ["NDVI"]})


with DAG(
    dag_id="baseline",
    schedule_interval="@daily",
    start_date=datetime(2024, 7, 21),
    catchup=False,
) as dag1:
    process = create_data_process_task(task_id="data_processing")
    train = PythonOperator(task_id="training", python_callable=train_baseline)

    process >> train

with DAG(
    dag_id="useful",
    schedule_interval=None,
    start_date=datetime(2021, 8, 24),
) as dag2:
    process = create_data_process_task(task_id="data_processing")
    train = PythonOperator(task_id="training", python_callable=train_useful)

    process >> train

with DAG(
    dag_id="dummy",
    schedule_interval=None,
    start_date=datetime(2021, 8, 24),
) as dag3:
    process = create_data_process_task(task_id="data_processing")
    train = PythonOperator(task_id="training", python_callable=train_dummy)

    process >> train

with DAG(
    dag_id="ndvi",
    schedule_interval=None,
    start_date=datetime(2021, 8, 24),
) as dag3:
    process = create_data_process_task(task_id="data_processing")
    train = PythonOperator(task_id="training", python_callable=train_ndvi)

    process >> train
