import secrets
import string
from typing import Dict

import mlflow
import numpy as np
import omegaconf
import tensorflow as tf
import wandb
from hydra import compose, initialize_config_dir
from omegaconf import DictConfig
from rich.logging import RichHandler
from rich.traceback import install
from wandb.integration.keras import WandbMetricsLogger

AUTOTUNE = tf.data.AUTOTUNE
print(tf.__version__)
import glob
import logging
import os

import keras
from keras import layers

from . import parse_data

tf.compat.v1.set_random_seed(23)

CONFIG_PATH = "/usr/local/airflow/conf"

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()


# default image side dimension (65 x 65 square)
IMG_DIM = 65
# use 7 out of 10 bands for now
NUM_CLASSES = 4

NUM_TRAIN = 500
NUM_VAL = 320


def get_dataset(filelist, batch_size, buffer_size, keylist=["B4", "B3", "B2"]):
    dataset = parse_data.read_processed_tfrecord(filelist, keylist=keylist)
    dataset = dataset.shuffle(buffer_size)
    dataset = dataset.batch(batch_size)
    return dataset


def class_weights() -> Dict[int, int]:
    # define class weights to account for uneven distribution of classes
    # distribution of ground truth labels:
    # 0: ~60%
    # 1: ~15%
    # 2: ~15%
    # 3: ~10%
    class_weights = {}
    class_weights[0] = 1.0
    class_weights[1] = 4.0
    class_weights[2] = 4.0
    class_weights[3] = 6.0
    return class_weights


def construct_baseline_model(cfg: DictConfig) -> keras.Sequential:
    num_bands = len(cfg.features.list)
    lr = cfg.model.learning_rate
    model = keras.Sequential(
        [
            keras.Input(shape=[IMG_DIM, IMG_DIM, num_bands]),
            layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Conv2D(128, kernel_size=(3, 3), activation="relu"),
            layers.Conv2D(128, kernel_size=(3, 3), activation="relu"),
            layers.MaxPooling2D(pool_size=(2, 2)),
            layers.Dropout(0.2),
            layers.Flatten(),
            layers.Dense(units=50, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(NUM_CLASSES, activation="softmax"),
        ]
    )
    ths = list(np.arange(0, 0.99, 0.01))
    metrics = []
    # Compute precision and recall at every epoch for every class
    if cfg.logging.style == "wandb":
        for i in range(NUM_CLASSES):
            name1 = f"pr_{i}"
            name2 = f"re_{i}"
            m1 = keras.metrics.Precision(thresholds=ths, class_id=i, name=name1)
            m2 = keras.metrics.Recall(thresholds=ths, class_id=i, name=name2)
            metrics.append(m1)
            metrics.append(m2)

    # Also compute accuracy
    metrics.append("accuracy")

    model.compile(
        loss="categorical_crossentropy",
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        metrics=metrics,
    )
    return model


def train_model(
    model_config="default",
    features_config="default",
    logging_config="default",
    **override_args,
):
    initialize_config_dir(
        version_base=None, config_dir=CONFIG_PATH, job_name="train_model"
    )
    cfg = compose(
        config_name="config",
        overrides=[
            f"model={model_config}",
            f"features={features_config}",
            f"logging={logging_config}",
        ],
        *[f"{k}={v}" for k, v in override_args.items()],
    )
    train_cnn(cfg)


def generate_random_id(N=4):
    res = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for i in range(N)
    )
    return res


def train_cnn(cfg: DictConfig):
    # load training data in TFRecord format
    filelist = glob.glob("data/droughtwatch_data/train/processed_part*")

    buffer_size = NUM_TRAIN
    # Model related settings
    keylist = cfg.features.list
    batch_size = cfg.model.batch_size
    epochs = cfg.model.epochs
    # Get logging style and options
    logging_style = cfg.logging.style
    print(cfg)

    train_dataset = get_dataset(filelist, batch_size, buffer_size, keylist=keylist)
    filelist = glob.glob("data/droughtwatch_data/val/processed_part*")
    buffer_size = NUM_VAL
    val_dataset = get_dataset(filelist, batch_size, buffer_size, keylist=keylist)
    PROJECT_NAME = "droughtwatch_capstone"

    model = construct_baseline_model(cfg)

    if logging_style == "wandb":
        # Do cloud-based wandb logging
        try:
            key = os.environ["WANDB_API_KEY"]
        except KeyError:
            logger.critical(
                "Logging style was set to wandb, but the WANDB_API_KEY is not set. Make sure to change it inside the .env file!"
            )
            exit(-1)
        wandb.login(key=key)
        run_name = f"{cfg.model.name}_{generate_random_id()}"

        # initialize wandb logging for your project and save your settings

        wandb.init(name=run_name, project=PROJECT_NAME)

        config = omegaconf.OmegaConf.to_container(
            cfg, resolve=True, throw_on_missing=True
        )
        config.pop("logging")
        wf_cfg = wandb.config
        wf_cfg.setdefaults(config)
        callbacks = [WandbMetricsLogger()]
    elif logging_style == "mlflow":
        # Do local MLFlow logging
        mlflow.set_tracking_uri("http://mlflow-server:5012")
        mlflow.set_experiment(PROJECT_NAME)
        run = mlflow.start_run(run_id=f"{cfg.model.name}_{generate_random_id()}")
        callbacks = [mlflow.keras.callback.MlflowCallback(run)]

    if epochs > 0:
        history = model.fit(
            train_dataset,
            epochs=epochs,
            validation_data=val_dataset,
            class_weight=class_weights(),
            callbacks=callbacks,
        )
    if logging_style == "mlflow":
        mlflow.keras.log_model(model, "artifacts")
        mlflow.end_run()


if __name__ == "__main__":
    train_model(model_config="default", logging_config="mlflow")
