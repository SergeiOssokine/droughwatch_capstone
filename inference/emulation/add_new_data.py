import datetime
import json
import logging
import os
import time

import boto3
import typer
from hydra import compose, initialize
from omegaconf import DictConfig
from rich.logging import RichHandler
from rich.progress import Progress
from rich.traceback import install
from statemachine import StateMachine
from typing_extensions import Annotated

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


mpath = os.path.dirname(__file__)
data_dir = os.path.join(mpath, "../../training/airflow/data/droughtwatch_data/val")
ref_data = os.path.join(mpath, "reference_data.parquet")


def add_new_data(s3_client, bucket_name: str, data_file_path: str, date: str) -> None:
    data_file_name = os.path.basename(data_file_path)
    remote_filepath = os.path.join(date, data_file_name)
    logger.info(f"Uploading {bucket_name}/{remote_filepath}")
    _ = s3_client.upload_file(data_file_path, bucket_name, remote_filepath)


def simulate_inference_on_data_add(
    config: DictConfig, interval: float = 20.0, n_days=5
):
    s3_client = boto3.client("s3")
    data_bucket = config.infra.inference.data_bucket
    pipeline_name = config.infra.inference.step_function.pipeline_name
    payload = json.dumps(f'{{"data_bucket_name":"{data_bucket}"}}')
    # Upload the reference data
    logger.info(f"Uploading the reference data to {data_bucket}")
    # add_new_data(s3_client, data_bucket, ref_data, "")
    base = datetime.date(2024, 8, 7)
    date_list = [str(base + datetime.timedelta(days=x)) for x in range(n_days)]
    sfn = boto3.client("stepfunctions")
    logger.info("Preparing the state machine")
    sm = StateMachine(sfn, pipeline_name, payload)
    logger.info("Launching the upload and inference")
    with Progress() as progress:
        task = progress.add_task("[green] Processing...", total=n_days)
        for i, date in enumerate(date_list):

            data_file_path = os.path.join(data_dir, f"part-r-{i:05d}")
            # Upload the raw data
            add_new_data(s3_client, data_bucket, data_file_path, date)
            time.sleep(1)

            # Run the pipeline
            response = sm.blocking_execution()
            if response["status"] != "SUCCEEDED":
                logger.error("Pipeline failed! Below is the error")
                logger.error(response["error"])
                break
            time.sleep(interval)
            progress.advance(task)
    logger.info("All done")


def main():
    conf_path = "../../setup/conf"
    logger.info(f"Reading the top-level configuration in {os.path.abspath(conf_path)}")
    # Initialize Hydra
    initialize(config_path=conf_path, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")
    simulate_inference_on_data_add(cfg)


if __name__ == "__main__":
    typer.run(main)
