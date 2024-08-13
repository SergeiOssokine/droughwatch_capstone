"""
This module contains the code that performs inference on processed data.
"""

import json
import os
import tempfile
import traceback
from typing import Any, Dict, List, Tuple

import awswrangler as wr
import boto3
import numpy as np
import onnxruntime as rt
import pandas as pd
import parse_data
import psycopg
import tensorflow as tf
from db_helper import SqlUpdate, get_credentials, update_table
from omegaconf import DictConfig, OmegaConf

# In case we are running on localstack
AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")
DROUGHTWATCH_DB = "droughtwatch"
LEDGER = "ledger"

# A list of all possible features that can appear in a processed dataset
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
    feature_list: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
    shuffle: bool = True,
):
    """Return a batched and optionally shuffled dataset. The input should correspond
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
    if feature_list is None:
        # Use RGB bands as default
        feature_list = ["B2", "B3", "B4"]
    if features is None:
        features = features_inference
    dataset = parse_data.read_processed_tfrecord(
        filelist, keylist=feature_list, features=features
    )
    if shuffle:
        dataset = dataset.shuffle(buffer_size)
    dataset = dataset.batch(batch_size)
    return dataset


def get_model(s3, path: str) -> Tuple[bytes, DictConfig]:
    """Give the path to the model, get the model and its
    configuration

    Args:
        s3 (s3 client): The s3 client
        path (str): The path to the model

    Returns:
        Tuple[bytes, DictConfig]: Serialized model, model config
    """
    # Load model
    registry_bucket_name = os.environ.get("model_registry_s3_bucket")
    response = s3.get_object(
        Bucket=registry_bucket_name, Key=os.path.join(path, "model.onnx")
    )
    # The model at this point is a binary object
    model = response["Body"].read()
    # Load config
    response = s3.get_object(
        Bucket=registry_bucket_name, Key=os.path.join(path, "config.yaml")
    )
    content = response["Body"].read()
    config = OmegaConf.create(content.decode("utf-8"))
    return model, config


def run_inference(model: bytes, dset) -> Tuple[np.ndarray, np.ndarray]:
    """Run the model on the data

    Args:
        model (bytes): The serialized ONNX model in memory
        dset (TFRecordsDataset): The dataset

    Returns:
        Tuple[np.ndarray, np.ndarray]: The predictions and associated IDs
    """
    providers = ["CPUExecutionProvider"]
    # Initialize the ONNX run-time.
    m = rt.InferenceSession(model, providers=providers)
    input_name = m.get_inputs()[0].name
    all_onnx_preds = []
    all_ids = []
    for batch in dset:
        # Note that batch is a tuple
        # (tensor of features, tensor of labels, tensor of ids)
        # The tensor of features has shape (n_cases, IMG_DIM, IMG_DIM,n_features)
        # We use tensor of features as input, ignore the labels
        # and store the ids.
        inputs = {input_name: batch[0].numpy()}
        ids = [x.decode("utf-8") for x in batch[2].numpy()]
        onnx_pred = m.run(None, inputs)
        tmp = np.array(onnx_pred)
        all_onnx_preds.append(tmp.reshape(tmp.shape[1], tmp.shape[2]))
        all_ids.extend(ids)

    result_onnx = np.vstack(all_onnx_preds)
    return result_onnx, np.array(all_ids)


def package_predictions(
    model_results: np.ndarray, case_ids: np.ndarray
) -> pd.DataFrame:
    """Package the model predictions into a DataFrame

    Args:
        model_results (np.ndarray): The probabilities of each class
        case_ids (np.ndarray): The unique ids for every image

    Returns:
        pd.DataFrame: Dataframe of predictions
    """
    class_label = np.argmax(model_results, axis=-1)
    p_class_label = np.amax(model_results, axis=-1)
    model_results = np.hstack(
        (
            case_ids[:, None],
            model_results,
            class_label[:, None],
            p_class_label[:, None],
        )
    )
    # Store the probabilities of each class, the actual predicted label,
    # and the probability of that label
    df = pd.DataFrame(
        model_results,
        columns=["ID", "P_0", "P_1", "P_2", "P_3", "label", "P_label"],
    )
    df = df.astype(
        dtype={
            "ID": "string",
            "P_0": "float64",
            "P_1": "float64",
            "P_2": "float64",
            "P_3": "float64",
            "label": "int64",
            "P_label": "float64",
        }
    )
    return df


def get_new_cases(db_config: Dict[str, str | int | float]) -> List[str]:
    """Find all cases where the processed data exists but no predictions
    are available.

    Args:
        db_config (Dict[str, str  |  int  |  float]): Database config

    Returns:
        List[str]: Names of all the processed files with no predictions
    """
    with psycopg.connect(  # pylint: disable=E1129
        f"host={db_config['host']} port={db_config['port']} dbname={DROUGHTWATCH_DB} user={db_config['username']} password={db_config['password']}",
        autocommit=True,
    ) as conn:
        df = pd.read_sql(f'select * from "{LEDGER}"', conn)
        new_cases = df[(df["processed_path"].notna()) & (df["predictions_path"].isna())]
    return new_cases["processed_path"].values


def lambda_handler(event, context) -> Dict[str, Any]:
    """Lambda handler for inference. Performs the following actions:
    - Find all processed files with no predictions
    - Loops over them and runs the model
    - Saves the predictions back to S3
    - Updates the ledger DB to indicate which files have been
    processed

    Args:
        event
        context

    Returns:
        Dict[str,Any]:The body of the response in json form
    """
    try:
        # Data from previous step
        ev = event["body"]
        data_bucket_name = ev["data_bucket_name"]
        # Load the model and its config
        s3_model_path = ev.get("model_path", os.environ.get("model_path"))
        if AWS_ENDPOINT_URL is not None:
            s3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
            wr.config.s3_endpoint_url = AWS_ENDPOINT_URL
        else:
            s3 = boto3.client("s3")
        model, config = get_model(s3, s3_model_path)

        # Get new cases from ledger database
        db_config = get_credentials(endpoint_url=AWS_ENDPOINT_URL)
        new_cases = get_new_cases(db_config)

        # For every case that does not have predictions, run the model
        for key in new_cases:
            name = os.path.basename(key)
            base_dir = os.path.dirname(key)
            with tempfile.TemporaryDirectory() as tmpdirname:
                tmp_file = os.path.join(tmpdirname, name)
                # Get the processed datfile
                with open(tmp_file, "w+b") as f:
                    s3.download_fileobj(
                        data_bucket_name, os.path.join(base_dir, name), f
                    )
                dset = get_dataset(
                    tmp_file,
                    feature_list=config.features.list,
                    batch_size=64,
                    buffer_size=64,
                    shuffle=False,
                )
                # Get the results and write them back to s3
                inf_res, ids = run_inference(model, dset)
                df = package_predictions(inf_res, ids)
                predictions_path = os.path.join(base_dir, "predictions.parquet")
                wr.s3.to_parquet(
                    df=df,
                    path=f"s3://{data_bucket_name}/{predictions_path}",
                    compression=None,
                )
            # Update the ledger, recording that this file has predictions
            u = SqlUpdate("predictions_path", predictions_path)
            cond = f"processed_path='{key}'"
            update_table("ledger", DROUGHTWATCH_DB, u, cond, db_config)
        # Return a code for success and pass on the input event
        return {"statusCode": 200, "body": ev}
    except Exception as e:  # pylint: disable=W0718
        # Something has gone wrong, capture the traceback
        tb_string = traceback.format_exc()
        print(tb_string)
        # Make sure to return the exception and traceback in the response
        return {
            "statusCode": 500,
            "body": json.dumps({"Exception": str(e), "Traceback": tb_string}),
        }


if __name__ == "__main__":
    event = {
        "body": {
            "data_bucket_name": "droughtwatch-data",
            "model_registry_s3_bucket": "droughtwatch-model",
            "model_path": "sample_model/baseline",
        }
    }
    lambda_handler(event, None)
