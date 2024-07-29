import io
import os
import tempfile
from typing import Dict, List

import awswrangler as wr
import boto3
import numpy as np
import onnx
import onnxruntime as rt
import pandas as pd
import parse_data
import tensorflow as tf
from omegaconf import OmegaConf
from parse_data import process_one_dataset

AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")


features_inference = {
    "B1": tf.io.FixedLenFeature([], tf.string),
    "B2": tf.io.FixedLenFeature([], tf.string),
    "B3": tf.io.FixedLenFeature([], tf.string),
    "B4": tf.io.FixedLenFeature([], tf.string),
    "B5": tf.io.FixedLenFeature([], tf.string),
    "B6": tf.io.FixedLenFeature([], tf.string),
    "B7": tf.io.FixedLenFeature([], tf.string),
    "B8": tf.io.FixedLenFeature([], tf.string),
    "B9": tf.io.FixedLenFeature([], tf.string),
    "B10": tf.io.FixedLenFeature([], tf.string),
    "B11": tf.io.FixedLenFeature([], tf.string),
    "NDVI": tf.io.FixedLenFeature([], tf.string),
    "NDMI": tf.io.FixedLenFeature([], tf.string),
    "EVI": tf.io.FixedLenFeature([], tf.string),
    "id": tf.io.FixedLenFeature([], tf.string),
}


def get_dataset(
    filelist: List[str],
    batch_size: int,
    buffer_size: int,
    keylist: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
    shuffle: bool = True,
):
    """Return a batched and shuffled dataset. The input should correspond
    to processed files.

    Args:
        filelist (List[str]): List of files comprising the processed TFRecords dataset
        batch_size (int): The batch size
        buffer_size (int): The buffer size for shuffling
        keylist (List[str], optional): The list of features to return.
        shuffle (bool, optional): Determines if we shuffle the dataset. Defaults to True.

    Returns:
        tf.Dataset: The dataset ready for training/validation
    """
    if keylist is None:
        # Use RGB bands as default
        keylist = ["B2", "B3", "B4"]
    if features is None:
        features = features_inference
    dataset = parse_data.read_processed_tfrecord(
        filelist, keylist=keylist, features=features
    )
    if shuffle:
        dataset = dataset.shuffle(buffer_size)
    dataset = dataset.batch(batch_size)
    return dataset


def get_model(s3, path):
    # Load model
    registry_bucket_name = os.environ.get("model_registry_s3_bucket")
    response = s3.get_object(
        Bucket=registry_bucket_name, Key=os.path.join(path, "model.onnx")
    )
    # content = response['Body'].read()
    # model = onnx.load(io.BytesIO(content))
    model = response["Body"].read()
    # Load config
    response = s3.get_object(
        Bucket=registry_bucket_name, Key=os.path.join(path, "config.yaml")
    )
    content = response["Body"].read()
    config = OmegaConf.create(content.decode("utf-8"))
    return model, config


def run_inference(model, dset):
    providers = ["CPUExecutionProvider"]
    m = rt.InferenceSession(model, providers=providers)
    input_name = m.get_inputs()[0].name
    all_onnx_preds = []
    all_ids = []
    for batch in dset:
        inputs = {input_name: batch[0].numpy()}
        ids = [
            x.decode("utf-8") for x in batch[2].numpy()
        ]  # .tobytes().decode("utf-8")

        onnx_pred = m.run(None, inputs)
        tmp = np.array(onnx_pred)
        all_onnx_preds.append(tmp.reshape(tmp.shape[1], tmp.shape[2]))
        all_ids.extend(ids)

    result_onnx = np.vstack(all_onnx_preds)
    return result_onnx, np.array(all_ids)


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
    data_bucket_name = event["data_bucket_name"]
    s3_model_path = event.get("model_path", os.environ.get("model_path"))

    if AWS_ENDPOINT_URL is not None:
        s3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
        wr.config.s3_endpoint_url = AWS_ENDPOINT_URL
    else:
        s3 = boto3.client("s3")
    model, config = get_model(s3, s3_model_path)
    keylist = config.features.list

    response = s3.list_objects_v2(
        Bucket=data_bucket_name,
    )
    names = []
    for c in response["Contents"]:
        key = c["Key"]
        if ("processed" not in key) or ("parquet" in key):
            continue
        name = os.path.basename(key)
        base_dir = os.path.dirname(key)
        names.append(name)
        with tempfile.TemporaryDirectory() as tmpdirname:
            print("created temporary directory", tmpdirname)
            tmp_file = os.path.join(tmpdirname, name)
            with open(tmp_file, "w+b") as f:
                s3.download_fileobj(data_bucket_name, key, f)
            dset = get_dataset(
                tmp_file, keylist=keylist, batch_size=64, buffer_size=64, shuffle=False
            )
            inf_res, ids = run_inference(model, dset)
            class_label = np.argmax(inf_res, axis=-1)
            p_class_label = np.amax(inf_res, axis=-1)
            inf_res = np.hstack(
                (ids[:, None], inf_res, class_label[:, None], p_class_label[:, None])
            )
            df = pd.DataFrame(
                inf_res, columns=["ID", "P_0", "P_1", "P_2", "P_3", "label", "P_label"]
            )
            wr.s3.to_parquet(
                df=df,
                path=f"s3://{data_bucket_name}/{os.path.join(base_dir, 'predictions.parquet')}",
                compression=None,
            )

    return {"statusCode": 200, "body": {"names": names}}


if __name__ == "__main__":
    event = {
        "data_bucket_name": "droughtwatch",
        "model_registry_s3_bucket": "droughtwatch-capstone-8121e039-a4ec-4e7b-9b82-cdfc39520157",
        "s3_model_path": "baseline",
    }
    lambda_handler(event, None)
