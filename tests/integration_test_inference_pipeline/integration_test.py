"""
Main driver script to perform an-end-to-end integration test
The only thing outside of this is launching localstack with
docker-compose.
"""

import glob
import json
import logging
import os
import sys

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
    print(lst)
    for it in lst:
        fname = os.path.basename(it)
        local_filepath = os.path.join(path, fname)
        remote_filepath = local_filepath
        _ = s3_client.upload_file(local_filepath, bucket_name, remote_filepath)


def setup_secret(config):
    sm = boto3.client("secretsmanager", endpoint_url=config.aws_endpoint_url)
    with open(config.db_secret, "r") as fp:
        secret_payload = json.dumps(json.load(fp))

    try:
        sm.create_secret(
            Name="DB_CONN",
            Description="Secret for connecting to DB",
            SecretString=secret_payload,
        )
    except sm.exceptions.ResourceExistsException:
        pass


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

    logger.info("Setting up sample reference data")
    setup_sample(s3_client, config.reference_path, config.data_bucket_name)
    logger.info("Setting up a new secret to connect to database")
    setup_secret(config)


def write_env_file(config, env_file_name=".env"):
    with open(env_file_name, "w") as fw:
        for key, value in config.items():
            fw.write(f"{key}={value}\n")


def main(
    config: Annotated[str, typer.Option(help="The config file to use")] = "config.yaml",
    setup_only: Annotated[
        bool, typer.Option(help="Whether to only do setup but not run the tests")
    ] = False,
    dump_env_file: Annotated[
        bool,
        typer.Option(help="Whether to dump an env file that can be used with docker"),
    ] = False,
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
    if dump_env_file:
        write_env_file(config)
    if setup_only:
        sys.exit(0)
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
    expectation_inference = {"sample_data/28_07_24/predictions.parquet": 14581}
    payload_inference = {"body": {"data_bucket_name": "droughtwatch-data"}}
    st = {
        "expectation": expectation_inference,
        "target": "parquet",
        "payload": payload_inference,
    }
    integration_test(config, "inference", st)
    # Run the observability integration test
    expectation_observe = {
        "predictions_path": {0: "sample_data/28_07_24/predictions.parquet"},
        "class_0_frac": {0: 0.4700854700854701},
        "class_1_frac": {0: 0.10256410256410256},
        "class_2_frac": {0: 0.15384615384615385},
        "class_3_frac": {0: 0.27350427350427353},
        "most_common_percentage": {0: 47.01},
        "share_missing_values": {0: 0.0},
        "prediction_drift": {0: 0.1674621565443287},
    }
    st = {
        "expectation": expectation_observe,
        "target": "db",
        "payload": payload_inference,
    }
    integration_test(config, "observe", st)
    logger.info("Integration test completed.")


if __name__ == "__main__":
    typer.run(main)
