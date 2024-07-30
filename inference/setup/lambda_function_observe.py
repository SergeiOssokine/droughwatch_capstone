import os
import tempfile
from typing import List

import boto3

AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")


def lambda_handler(event, context):
    ev = event["body"]
    bucket_name = ev["data_bucket_name"]
    if AWS_ENDPOINT_URL is not None:
        s3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
    else:
        s3 = boto3.client("s3")

    print(f"S3_ENDPOINT_URL={AWS_ENDPOINT_URL}")

    return {"statusCode": 200}


if __name__ == "__main__":
    event = {
        "data_bucket_name": "droughtwatch",
    }
    lambda_handler(event, None)
