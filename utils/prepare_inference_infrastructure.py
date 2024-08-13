"""Module to help setup the necessary infrastructure for
inference. In particular, sets up terraforms vars, builds
the Lambda image and pushes it to an ECR repo.
"""

import base64
import logging
import os
import subprocess as sp

import boto3
import docker
from conf_utils import dict_generator
from hydra import compose, initialize
from omegaconf import DictConfig, OmegaConf
from rich.logging import RichHandler
from rich.traceback import install

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


def setup_terraform_default_vars(cfg: DictConfig, path_to_vars: str) -> None:
    """Writes the terraform .tfvars file based on the yaml config provided.
    The result is used when provisioning inference infrastructure with tf.

    Args:
        cfg (DictConfig): The config dictionary constructed by hydra
        path_to_vars (str): The absolute path (including file name) to
            the .tfvars file
    """
    logger.info(f"Updating the terraform variables in {path_to_vars}")
    infra_config = cfg.infra
    config_gen = dict_generator(OmegaConf.to_container(infra_config.inference))
    with open(path_to_vars, "w", encoding="utf-8") as fw:
        for it in config_gen:
            key, val = it[-2:]
            if isinstance(val, str):
                fw.write(f'{key}\t=\t"{val}"\n')
            else:
                fw.write(f"{key}\t=\t{val}\n")

        fw.write(f'model_bucket\t=\t"{cfg.training.model_registry_s3_bucket}"')


if __name__ == "__main__":
    CONF_PATH = "../setup/conf"
    TF_PATH = os.path.join(
        os.path.dirname(__file__), "../inference/setup/tf/vars/droughtwatch.tfvars"
    )
    logger.info(f"Reading the top-level configuration in {os.path.abspath(CONF_PATH)}")
    # Initialize Hydra
    initialize(config_path=CONF_PATH, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")
    setup_terraform_default_vars(cfg, TF_PATH)
    config = OmegaConf.to_container(cfg.infra)
    config.pop("training")
    logger.info("Getting the auth token from ECR")
    ecr_client = boto3.client("ecr", region_name=config["aws_region"])
    response = ecr_client.get_authorization_token()
    repo_name = cfg.infra.inference.lambda_func.lambda_image_name.split(":")[0]
    logger.info(f"Creating the {repo_name} repository on ECR")
    try:
        ecr_client.create_repository(repositoryName=repo_name)
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        logger.info("Repository already exsists, continuing")

    adata = response["authorizationData"][0]
    username, password = (
        base64.b64decode(adata["authorizationToken"]).decode("utf-8").split(":")
    )
    registry = adata["proxyEndpoint"]
    docker_client = docker.from_env()
    TAG = "v0.1"
    local_name = f"inference:{TAG}"
    logger.info(f"Building local image {local_name}")
    docker_cmd = (
        'docker build --build-arg="PREFIX=inference/setup" -f '
        f'inference/setup/Dockerfile -t {local_name} .'
    )
    sp.check_call(
        docker_cmd,
        shell=True,
    )

    ecr_image = f"{registry[8:]}/{cfg.infra.inference.lambda_func.lambda_image_name}"
    local_image = docker_client.images.get(local_name)
    logger.info(f"Tagging it with the remote uri: {ecr_image}")
    local_image.tag(ecr_image)
    logger.info("Logging into the ECR")
    regClient = docker_client.login(username, password, registry=registry)
    logger.info("Pushing the image")
    push_logs = docker_client.images.push(ecr_image)
    logger.info("Done")
