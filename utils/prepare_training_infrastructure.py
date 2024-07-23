import logging
import os
import subprocess as sp
from typing import Dict, List

import boto3
from hydra import compose, initialize
from omegaconf import DictConfig, OmegaConf
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax
from rich.traceback import install

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


def dict_generator(adict, pre: List = None):
    pre = pre[:] if pre else []
    if isinstance(adict, dict):
        for key, value in adict.items():
            if isinstance(value, dict):
                yield from dict_generator(value, pre + [key])
            elif isinstance(value, (list, tuple)):
                for v in value:
                    yield from dict_generator(v, pre + [key])
            else:
                yield pre + [key, value]
    else:
        yield pre + [adict]


def validate_dict(cfg: DictConfig) -> None:
    """Iterate over the configuration and check for unset (None)
    values, then hilight those if found and exit

    Args:
        cfg (DictConfig): Top-level config for the project
    """
    fail = False
    conf = OmegaConf.to_container(cfg, resolve=True, throw_on_missing=True)

    gen = dict_generator(conf)
    for item in gen:
        param = ".".join(item[:-1])
        val = item[-1]
        if val is None:
            logger.error(f"{param} is unset. Please examine the top-level config file")
            fail = True
    if fail:
        logger.critical("Validation failed! Exiting")
        exit(1)


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


if __name__ == "__main__":
    pth = "../setup/conf"
    logger.info(f"Reading the top-level configuration in {os.path.abspath(pth)}")
    # Initialize Hydra
    initialize(config_path=pth, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")

    logger.info("The following is the complete configuration of the project")
    console = Console()
    syntax = Syntax(OmegaConf.to_yaml(cfg), "yaml", theme="ansi_light")
    console.print(syntax)
    logger.info("Validating the configuration")
    validate_dict(cfg)
    logger.info("Validation successul")

    # Create bucket for model registry
    make_model_registry_bucket(cfg)

    # Append the secrets to the env file
    secrets = cfg.secrets_path
    logger.info(f"Appending the contents of {secrets} to the .env file")
    sp.check_call(f"cat {secrets} >> ./setup/.env", shell=True)
    logger.info("Done")
