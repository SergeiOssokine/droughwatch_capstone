"""
Cleans up inference infrastructure that was *not* provisioned
by terraform:

- the S3 model registry bucket
- the ECR repo with the model
"""

import logging
import os

import boto3
from hydra import compose, initialize
from rich.logging import RichHandler
from rich.traceback import install

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()

if __name__ == "__main__":
    CONF_PATH = "../setup/conf"
    logger.info(f"Reading the top-level configuration in {os.path.abspath(CONF_PATH)}")
    # Initialize Hydra
    initialize(config_path=CONF_PATH, version_base=None)
    # Compose with overrides
    cfg = compose(config_name="config")
    # Delete the model registry bucket
    bucket_name = cfg.training.model_registry_s3_bucket
    logger.info(f"Cleaning up the S3 model registry bucket: {bucket_name}")
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    # First we empty the bucket
    logger.info("Emptying the bucket")
    bucket.objects.all().delete()
    # Now we delete it
    logger.info("Deleting the bucket")
    bucket.delete()
    # Delete the ECR repo
    repo_name = cfg.infra.inference.lambda_func.lambda_image_name.split(":")[0]
    logger.info(f"Cleaning up the ECR registry: {repo_name} ")
    ecr_client = boto3.client("ecr", region_name=cfg.infra.aws_region)
    ecr_client.delete_repository(repositoryName=repo_name, force=True)
    logger.info("Done")
