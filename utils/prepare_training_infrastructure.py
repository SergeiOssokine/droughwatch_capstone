import logging
import os
import subprocess as sp

import boto3
from conf_utils import validate_dict
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


def make_model_registry_bucket(cfg: DictConfig) -> None:
    """Create an s3 bucket for the model registry. Controlled by
    training.model_registry_s3_bucket config variable.

    Args:
        cfg (DictConfig): Top-level config for the project
    """
    logger.info("Creating S3 bucket for the model registry")
    bucket_name = cfg.training.model_registry_s3_bucket
    region = cfg.infra.aws_region
    s3 = boto3.resource("s3")

    # Hack around AWS S3 legacy behaviour
    # See https://stackoverflow.com/a/51912090/22288495

    if region != "us-east-1":
        s3.create_bucket(
            Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region}
        )
    else:
        s3.create_bucket(Bucket=bucket_name)
    logger.info("Creation successful")


def assemble_env_file(cfg: DictConfig) -> None:
    logger.info("Assembling the .env file needed to configure Airflow docker")
    postgres_config = cfg.infra.training.postgres
    airflow_config = cfg.infra.training.airflow
    s3_bucket_name = cfg.training.model_registry_s3_bucket
    env_path = "./training/setup/.env"
    with open(env_path, "w") as fw:
        for k, v in postgres_config.items():
            fw.write(f"{k}={v}\n")
        for k, v in airflow_config.items():
            fw.write(f"{k}={v}\n")
        fw.write(f"S3_BUCKET_NAME={s3_bucket_name}\n")

    logger.info(f"Done. File created in {os.path.abspath(env_path)}")


if __name__ == "__main__":
    pth = "../setup/conf"
    logger.info(f"Reading the top-level configuration in {os.path.abspath(pth)}")
    # Initialize Hydra
    initialize(config_path=pth, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")

    logger.info("The following is the complete configuration of the project")
    console = Console()
    syntax = Panel(
        Syntax(OmegaConf.to_yaml(cfg, resolve=True), "yaml", theme="ansi_light"),
        title="config.yaml",
    )
    console.print(syntax)
    logger.info("Validating the configuration")
    validate_dict(cfg)
    logger.info("Validation successul")

    # Create bucket for model registry
    # make_model_registry_bucket(cfg)

    # Assemble the .env file for the docker-compose stack
    assemble_env_file(cfg)

    # Append the secrets to the env file
    secrets = cfg.secrets_path
    logger.info(f"Appending the contents of {secrets} to the .env file")
    sp.check_call(f"cat {secrets} >> ./training/setup/.env", shell=True)
    logger.info("Done")

    # Choose the CPU or GPU docker variant depending on configuration
    docker_config = "./training/setup/docker-compose.yml"
    if os.path.isfile(docker_config):
        os.unlink(docker_config)
    if cfg.infra.training.use_gpu_training:
        os.symlink("docker-compose.gpu.yml", docker_config)
    else:
        os.symlink("docker-compose.cpu.yml", docker_config)
