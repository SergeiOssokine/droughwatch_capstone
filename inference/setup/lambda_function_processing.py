import os
import tempfile
from typing import List

import boto3
from parse_data import process_one_dataset

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")


def get_all_folders(s3, bucket: str, s3_path: str) -> List[str]:
    """Return a list of all "folders" in s3 path

    Args:
        s3_path (str): The path to examine
    """
    response = s3.list_objects_v2(Bucket=bucket, Prefix=s3_path)
    folders = []
    for c in response["Contents"]:
        key = c["Key"]
        if "/" in key:
            folders.append(os.path.dirname(key))
    res = sorted(list(set(folders)))
    return res


def lambda_handler(event, context):

    bucket_name = event["bucket_name"]
    if S3_ENDPOINT_URL is not None:

        s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT_URL)
    else:
        s3 = boto3.client("s3")

    folders = get_all_folders(s3, bucket_name, "")
    print(folders)

    response = s3.list_objects_v2(
        Bucket=bucket_name,
    )

    for c in response["Contents"]:
        key = c["Key"]
        print(f"key:{key}")
        if key[-1] == "/" or "processed" in key:
            continue
        name = os.path.basename(key)
        base_dir = os.path.dirname(key)

        with tempfile.TemporaryDirectory() as tmpdirname:
            print("created temporary directory", tmpdirname)
            tmp_file = os.path.join(tmpdirname, name)
            with open(tmp_file, "w+b") as f:
                s3.download_fileobj(bucket_name, key, f)

            processed_file = process_one_dataset(tmp_file, assign_id=True)
            with open(processed_file, "rb") as f:
                s3.upload_fileobj(
                    f,
                    bucket_name,
                    os.path.join(base_dir, os.path.basename(processed_file)),
                )
    return {
        "statusCode": 200,
    }


if __name__ == "__main__":
    event = {
        "bucket_name": "droughtwatch",
    }
    lambda_handler(event, None)
