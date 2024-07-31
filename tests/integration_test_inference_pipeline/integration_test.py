"""
Main driver script to perform an-end-to-end integration test
The only thing outside of this is launching localstack with
docker-compose.
"""

import glob
import logging
import os

import boto3
import typer
from omegaconf import DictConfig, OmegaConf
from perform_integration_test import integration_test
from rich.logging import RichHandler
from rich.traceback import install
from typing_extensions import Annotated

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


def setup_sample(s3_client: boto3.client, path: str, bucket_name: str) -> None:
    """Upload everything from path to s3 bucket.

    Args:
        s3_client (boto3.client): The instantiated s3 client
        path (str): The local path where files to upload are
        bucket_name (str): The bucket name to which to upload
    """
    s3_client.create_bucket(Bucket=bucket_name)
    tmp = os.path.join(path, "*")
    lst = glob.glob(tmp)
    for it in lst:
        fname = os.path.basename(it)
        local_filepath = os.path.join(path, fname)
        remote_filepath = local_filepath
        _ = s3_client.upload_file(local_filepath, bucket_name, remote_filepath)


def setup(config: DictConfig) -> None:
    """Set up the data and model needed for the integration test

    In particular, create s3 buckets for model and data and populate
    them with information from ./sample_data.

    Args:
        config (DictConfig): Configuration options
    """
    s3_client = boto3.client("s3", endpoint_url=config.aws_endpoint_url)
    # Put the data in S3 on localstack
    logger.info("Setting up sample data")
    setup_sample(s3_client, config.data_path, config.data_bucket_name)
    # Put the model in S3 on localstack
    logger.info("Setting up sample model")
    setup_sample(s3_client, config.model_path, config.model_registry_s3_bucket)


def main(
    config: Annotated[str, typer.Option(help="The config file to use")] = "config.yaml",
):
    """Main function that call the processing, inference and observability tests

    Args:
        config (Annotated[str, typer.Option, optional): The config file to use.
            Defaults to "config.yaml".
    """
    logger.info("Starting integration test")
    # Read config
    logger.info(f"Loading the config file, {config}")
    config = OmegaConf.load(config)
    # Setup: create the S3 buckets with sample data and sample model
    logger.info("Setting up for integration test")
    setup(config)
    # Run the processing integration test
    expectation_processing = {"sample_data/28_07_24/processed_part-r-00033": 27757899}
    payload_processing = {"data_bucket_name": "droughtwatch-data"}
    st = {
        "expectation": expectation_processing,
        "target": "processed",
        "payload": payload_processing,
    }
    integration_test(config, "processing", st)

    # Run the inference integration test
    expectation_inference = {"sample_data/28_07_24/predictions.parquet": 17586}
    payload_inference = {"body": {"data_bucket_name": "droughtwatch-data"}}
    st = {
        "expectation": expectation_inference,
        "target": "parquet",
        "payload": payload_inference,
    }
    integration_test(config, "inference", st)
    # Run the observability integration test

    logger.info("Integration test completed.")


if __name__ == "__main__":
    typer.run(main)
