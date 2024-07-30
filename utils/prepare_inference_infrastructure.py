import base64
import logging
import os
import subprocess as sp
from typing import Dict, List, Union

import boto3
import docker
from hydra import compose, initialize
from omegaconf import DictConfig, OmegaConf
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.syntax import Syntax
from rich.traceback import install

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


def get_account_id():
    client = boto3.client("sts")
    return client.get_caller_identity()["Account"]


if __name__ == "__main__":
    pth = "../setup/conf"
    logger.info(f"Reading the top-level configuration in {os.path.abspath(pth)}")
    # Initialize Hydra
    initialize(config_path=pth, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")
    config = OmegaConf.to_container(cfg.infra)
    config.pop("training")
    id = get_account_id()
    logger.info("Getting the auth token from ECR")
    ecr_client = boto3.client("ecr", region_name=config["aws_region"])
    response = ecr_client.get_authorization_token()
    repo_name = "droughtwatch-inference"
    logger.info(f"Creating the {repo_name} repository on ECR")
    try:
        ecr_client.create_repository(repositoryName=repo_name)
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        logger.info("Repository already exsists, continuing")
        pass

    adata = response["authorizationData"][0]
    username = "AWS"
    username, password = (
        base64.b64decode(adata["authorizationToken"]).decode("utf-8").split(":")
    )
    registry = adata["proxyEndpoint"]
    docker_client = docker.from_env()
    tag = "v0.1"
    local_name = f"inference:{tag}"
    logger.info(f"Building local image {local_name}")
    docker_client.images.build(path="./inference/setup/", tag=local_name)
    ecr_image = f"{registry[8:]}/{repo_name}:{tag}"
    local_image = docker_client.images.get(local_name)
    logger.info(f"Tagging it with the remote uri: {ecr_image}")
    local_image.tag(ecr_image)
    logger.info("Logging into the ECR")
    regClient = docker_client.login(username, password, registry=registry)
    logger.info("Pushing the image")
    push_logs = docker_client.images.push(ecr_image)
    logger.info("Done")
