"""
Performs a simple integration test by
launching the lambda container calling the lambda
API and then comparing the expected and recieved results.
Assumes everything is already set-up
"""

import json
import logging
import sys
import time
from typing import Any, Dict

import boto3
import pandas as pd
import psycopg
import requests
from deepdiff import DeepDiff
from omegaconf import DictConfig
from rich.logging import RichHandler
from rich.traceback import install
from test_utils import clean_up, launch_lambda_container, print_difference

logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()

LAMBDA_URL = "http://localhost:8080/2015-03-31/functions/function/invocations"


def get_credentials(endpoint_url: str | None = None) -> Dict[str, str]:
    """Get database credentials from AWS secrets manager

    Args:
        endpoint_url (str | None, optional): The endpoint url to use. Defaults to None.

    Returns:
        Dict[str, str]: The secrets
    """
    if endpoint_url:
        sm = boto3.client("secretsmanager", endpoint_url=endpoint_url)
    else:
        sm = boto3.client("secretsmanager")
    response = sm.get_secret_value(SecretId="DB_CONN")
    db_config = json.loads(response["SecretString"])
    tmp_host, tmp_port = db_config["host"].split(":")
    db_config["host"] = tmp_host
    db_config["port"] = tmp_port
    return db_config


def perform_checks(config: DictConfig, settings: Dict[str, Any], container) -> None:
    """Perform the integration test checks. For processing and inference
    lambdas, this involves checking that the right files were created at
    right spots with right sizes. For observe lambda, this involves parsing
    the database and making sure the results are correctly stored there

    Args:
        config (DictConfig): The overall config
        settings (Dict[str,Any]): The settings for this particular test
        container (_type_): The docker container that is running,
            we need it in case we have to clean up.
    """
    expectation = settings["expectation"]
    target = settings["target"]

    if "db" not in target:
        s3 = boto3.client("s3", endpoint_url=config.aws_endpoint_url)
        response_check = s3.list_objects_v2(
            Bucket=config.data_bucket_name, Prefix=config.data_path
        )
        result = {}
        for it in response_check["Contents"]:
            key = it["Key"]
            if target in key:
                result[key] = it["Size"]

        # We check the following:
        # 1. The processed data is present in the s3 bucket
        # 2. Check that the processed data is the right size
        if DeepDiff(result, expectation):
            logger.critical(
                "The lambda function result and the expectations [bold]differ[/bold]:"
            )
            logger.info("Cleaning up and exiting")
            print_difference(expectation, result)
            clean_up(container)
            sys.exit(1)
        else:
            logger.info("Result and expectation [bold]match[/bold]:")
            print_difference(expectation, result)
    else:
        # We need to get the final state of the metrics db
        db_config = get_credentials(endpoint_url=config.aws_endpoint_url)
        with psycopg.connect(
            f"host={db_config['host']} port={db_config['port']} dbname=droughtwatch user={db_config['username']} password={db_config['password']}",
            autocommit=True,
        ) as conn:
            sql = "select * from metrics;"
            result = pd.read_sql_query(sql, conn).to_dict()
            result.pop("timestamp")
            # We check that the results in the "metrics" database matches our expectations
            # We compare all columns except timestamp, for obvious reasons
            if DeepDiff(result, expectation, math_epsilon=1e-6):
                logger.critical(
                    "The lambda function result and the expectations differ:"
                )
                logger.info("Cleaning up and exiting")
                print_difference(expectation, result)
                clean_up(container)
                sys.exit(1)
            else:
                logger.info("Result and expectation [bold]match[/bold]:")
                print_difference(expectation, result)


def integration_test(config: DictConfig, name: str, settings: Dict[str, Any]) -> None:
    """Perform a single integration test for a given lambda.
    Will do the following
    - spin up the lambda container
    - set the right lambda handler
    - send an API request to the lambda with the payload
    - compare the resulting response to the expectations

    Args:
        config (DictConfig): The config to pass to the lambda docker
        name (str): The name of the lambda function to test
        settings (Dict[str, Any]): Local settings that describe
            test input/output
    """

    payload = settings["payload"]
    logger.info(f"Starting the {name} lambda integration test")
    # Launch the image with the correct CMD
    logger.info("Launching lambda docker container")
    container = launch_lambda_container(name, config)
    time.sleep(5)
    logger.info("Done")
    # Send request to the right port
    logger.info("Sending API request")
    response = requests.post(LAMBDA_URL, json=payload, timeout=500).json()
    body = response["body"]
    status = response["statusCode"]
    if status != 200:
        logger.critical(f"Received status {status}")
        logger.info(body)
        clean_up(container)
        sys.exit(1)

    logger.info(f"Response was {response}")
    # Perform checks
    logger.info("Performing checks")
    logger.info(
        "Will check the prediction file was created in right place with right size"
    )
    perform_checks(config, settings, container)

    logger.info("Checks completed!")
    logger.info("Cleaning up")
    clean_up(container)
    logger.info("Done")
