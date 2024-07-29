import logging
import sys

import boto3
import docker
import requests
from deepdiff import DeepDiff
from omegaconf import OmegaConf
from rich.logging import RichHandler
from rich.traceback import install
from test_utils import print_difference

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()

LAMBDA_URL = "http://localhost:8080/2015-03-31/functions/function/invocations"


def processing_integration_test(config):
    # Launch the image with the correct CMD
    logger.info("Starting the processing lambda integration test")
    logger.info("Launching lambda docker container")

    client = docker.from_env()
    container = client.containers.run(
        config.image,
        command=["lambda_function_processing.lambda_handler"],
        environment=OmegaConf.to_container(config, resolve=True, throw_on_missing=True),
        network_mode="host",
        detach=True,
    )
    logger.info("Done")

    # Send request to the right port
    payload = {"data_bucket_name": "droughtwatch-data"}
    logger.info("Sending API request")

    response = requests.post(LAMBDA_URL, json=payload)
    logger.info(f"Response was {response.content}")

    # Perform checks
    logger.info("Performing checks")
    logger.info(
        "Will check the processed data file was created in right place with right size"
    )
    s3 = boto3.client("s3", endpoint_url=config.aws_endpoint_url)
    response_check = s3.list_objects_v2(
        Bucket=config.data_bucket_name, Prefix=config.data_path
    )
    result = {}
    for it in response_check["Contents"]:
        key = it["Key"]
        if "processed" in key:
            result[key] = it["Size"]

    expected = {"sample_data/28_07_24/processed_part-r-00033": 27757899}

    # We check the following:
    # 1. The processed data is present in the s3 bucket
    # 2. Check that the processed data is the right size
    if DeepDiff(result, expected):
        logger.critical("The lambda function result and the expectations differ:")
        logger.info("Cleaning up and exiting")
        print_difference(expected, result)
        container.stop()
        container.remove()
        sys.exit(1)

    logger.info("Checks completed!")
    logger.info("Cleaning up")
    # Clean up
    container.stop()
    container.remove()
    logger.info("Done")
