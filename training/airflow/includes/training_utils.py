import secrets
import string
from sys import argv

import boto3
import omegaconf
import tensorflow as tf
import tf2onnx
from hydra import compose, initialize_config_dir

CONFIG_PATH = "/usr/local/airflow/conf"


def generate_random_id(N: int = 4) -> str:
    """Generate a simple alphanumeric ID of length N

    Args:
        N (int, optional): Length of the ID. Defaults to 4.

    Returns:
        str: The random ID
    """
    res = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for i in range(N)
    )
    return res


def upload_model_to_s3(model, model_name: str, bucket_name: str, config: str):
    s3 = boto3.client("s3")
    s3.put_object(Body=config, Bucket=bucket_name, Key=f"{model_name}/config.yaml")
    s3.put_object(
        Body=model.SerializeToString(),
        Bucket=bucket_name,
        Key=f"{model_name}/model.onnx",
    )


def convert_model_to_onnx(model):
    input_layer = tf.keras.layers.Input(batch_shape=model.input_shape)
    prev_layer = input_layer
    for layer in model.layers:
        prev_layer = layer(prev_layer)
    functional_model = tf.keras.models.Model(inputs=[input_layer], outputs=[prev_layer])

    # Now convert the Functional model to ONNX
    input_signature = (
        tf.TensorSpec(functional_model.input_shape, tf.float32, name="input"),
    )
    onnx_model, _ = tf2onnx.convert.from_keras(functional_model, input_signature)
    return onnx_model


if __name__ == "__main__":
    initialize_config_dir(
        version_base=None, config_dir=CONFIG_PATH, job_name="train_model"
    )

    cfg = compose(
        config_name="config",
    )
    config = omegaconf.OmegaConf.to_yaml(cfg.training, resolve=True)
    upload_model_to_s3("test", argv[1], config)
