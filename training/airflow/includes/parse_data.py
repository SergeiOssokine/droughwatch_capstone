import glob
import hashlib
import json
import logging
import os
from functools import partial
from typing import Dict, List, Tuple

import tensorflow as tf
from rich.logging import RichHandler
from rich.progress import track
from rich.traceback import install
from tensorflow import Tensor as Tensor
from tensorflow.data import Dataset

# Sets up the logger to work with rich
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(rich_tracebacks=True, markup=True))
logger.setLevel("INFO")
# Setup rich to get nice tracebacks
install()

# The bands and features in the raw data
raw_keylist = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
raw_features = {
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
    "label": tf.io.FixedLenFeature([], tf.int64),
}

# The bands and features in the processed data
keylist_processed = [
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B9",
    "B10",
    "B11",
    "NDVI",
    "NDMI",
    "EVI",
]

features_processed = {
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
    "label": tf.io.FixedLenFeature([], tf.int64),
    "NDVI": tf.io.FixedLenFeature([], tf.string),
    "NDMI": tf.io.FixedLenFeature([], tf.string),
    "EVI": tf.io.FixedLenFeature([], tf.string),
}

# default image side dimension (65 x 65 square)
IMG_DIM = 65
# Number of classes
NUM_CLASSES = 4


def parse_raw_tfrecord(
    serialized_example: str,
    keylist: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
) -> Tuple[Dict[str, Tensor], Tensor]:
    """Parse a single TFRecord file

    Args:
        serialized_example (str): The name of the file
        keylist (List[str] | None, optional): The features to return. Defaults to None.
        features (Dict[str, tf.io.FixedLenFeature] | None, optional): The map that describes
            all the features in the file. Defaults to None.
    """

    def getband(example_key: Tensor) -> Tensor:
        img = tf.io.decode_raw(example_key, tf.uint8)
        return tf.reshape(img[: IMG_DIM**2], shape=(IMG_DIM, IMG_DIM, 1))

    if keylist is None:
        keylist = raw_keylist
    if features is None:
        features = raw_features

    example = tf.io.parse_single_example(serialized_example, features)

    data_features = {}
    for key in keylist:
        band = getband(example[key])
        # Normalize the data to be between [0 and 1]
        data_features[key] = tf.cast(band, tf.float32) / 255.0
    label = tf.cast(example["label"], tf.int32)
    return data_features, label


def serialize_tensor(tensor: Tensor) -> tf.train.Feature:
    """Serialize a tensor to bytes

    Args:
        tensor (Tensor): The tensor to serialize

    Returns:
        tf.train.Feature: The feature representation of the tensor
    """
    tensor = tf.io.serialize_tensor(tensor)
    feature = tf.train.Feature(bytes_list=tf.train.BytesList(value=[tensor.numpy()]))
    return feature


def serialize_data(element: Tuple[Dict[str, Tensor], Tensor]) -> bytes:
    data_features = element[0]
    label = element[1]

    feature = {}
    for key, dnp in data_features.items():
        band_bytes = tf.io.serialize_tensor(dnp)
        feature[key] = tf.train.Feature(
            bytes_list=tf.train.BytesList(value=[band_bytes.numpy()])
        )

    feature["label"] = tf.train.Feature(int64_list=tf.train.Int64List(value=[label]))

    example = tf.train.Example(features=tf.train.Features(feature=feature))
    return example.SerializeToString()


def parse_tf_record(
    serialized_example: str,
    keylist: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
) -> Tuple[Tensor, Tensor]:
    if keylist is None:
        keylist = keylist_processed
    if features is None:
        features = features_processed
    example = tf.io.parse_single_example(serialized_example, features)
    bandlist = []
    for key in keylist:
        bandlist.append(
            tf.reshape(
                tf.io.parse_tensor(example[key], out_type=tf.float32),
                (IMG_DIM, IMG_DIM, 1),
            )
        )

    image = tf.concat(bandlist, -1)
    label = tf.cast(example["label"], tf.int32)
    # This is now actual data we want to use, so we one-hot encode the labels
    label = tf.one_hot(label, NUM_CLASSES)
    return image, label


def veto_missing(x: Dict[str, Tensor], y: Tensor) -> Tensor:
    bands = []
    for _, value in x.items():
        bands.append(value)
    image = tf.concat(bands, -1)
    return tf.reduce_max(image) > 1.0 / 255


def read_raw_tfrecord(
    path: str | List[str],
    keylist: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
) -> Dataset[Tuple[Dict[str, Tensor], Tensor]]:
    """Read one or many raw datasets. Will normalize the data and
    remove any blank images.

    Args:
        path (str | List[str]): The path to the raw data
        keylist (List[str] | None, optional): The features to use. Defaults to None.
        features (Dict[str, tf.io.FixedLenFeature] | None, optional): Mapping of each feature inside the file.
            Defaults to None.

    Returns:
        Dataset: The parsed dataset, as a dict with keys representing features
    """
    dataset = tf.data.TFRecordDataset(path)
    parsed_dataset = dataset.map(
        partial(parse_raw_tfrecord, keylist=keylist, features=features)
    )
    parsed_dataset = parsed_dataset.filter(veto_missing)  # type: ignore

    return parsed_dataset


def read_processed_tfrecord(
    path: List[str] | str,
    keylist: List[str] | None = None,
    features: Dict[str, tf.io.FixedLenFeature] | None = None,
) -> Dataset[Tuple[Tensor, Tensor]]:
    """Read one or many of the processed data files and convert them to format,
    suitable to training. In particular we have Tensors with shape
    (IMG_DIM,IMG_DIM,N_FEATURES) where N_FEATURES is len(keylist)

    Args:
        path (str | List[str]): The path to the processed data.
        keylist (List[str] | None, optional): The features to use. Defaults to None.
        features (Dict[str, tf.io.FixedLenFeature] | None, optional): Mapping of each feature inside the file.
            Defaults to None.
    Returns:
        Dataset: The parsed dataset, as a dataset of Tensors. The order of the last dimension is the same
            as the ordering of features in keylist.
    """
    raw_dataset = tf.data.TFRecordDataset(path)

    parsed_dataset = raw_dataset.map(
        partial(parse_tf_record, keylist=keylist, features=features)
    )

    return parsed_dataset


def write_processed_output(
    dataset: Dataset[Tuple[Dict[str, Tensor], Tensor]],
    out_name: str = "processed",
) -> None:
    """Write the processed output to disk.

    Args:
        dataset (Dataset): The processed output
        out_name (str, optional): The name of the output file. Defaults to "processed".
    """
    with tf.io.TFRecordWriter(out_name) as file_writer:
        for element in dataset:
            example = serialize_data(element)
            file_writer.write(example)
        file_writer.close()


def add_derived_features(
    data_features: Dict[str, Tensor], label: Tensor
) -> Tuple[Dict[str, Tensor], Tensor]:
    """Add additional features to the dataset which are derived
    from the raw data. Currently we add NDVI, NDMI and EVI.
    For a description of what these mean, consult here:
    https://www.usgs.gov/landsat-missions/landsat-surface-reflectance-derived-spectral-indices

    Args:
        data_features (Dict[str, Tensor]): The Dict with all of our features
        label (Tensor): The labels (not used)

    Returns:
        Tuple[Dict[str, Tensor], Tensor]: Updated Dict of
            features and labels.
    """
    # Function to add our new feature
    res: Dict[str, Tensor] = {}
    res.update(**data_features)
    r_band = data_features["B4"]
    b_band = data_features["B2"]
    nir_band = data_features["B5"]
    swir_band = data_features["B6"]
    # Calculate NDVI
    ndvi = (nir_band - r_band) / (r_band + nir_band + 1e-7)
    # Calculate NDMI
    ndmi = (nir_band - swir_band) / (nir_band + swir_band + 1e-7)
    # Calculate EVI
    G = 2.5
    c1 = 6
    c2 = -7.5
    L = 1
    evi = G * ((nir_band - r_band) / (nir_band + c1 * r_band + c2 * b_band + L))
    res["NDVI"] = ndvi
    res["NDMI"] = ndmi
    res["EVI"] = evi

    return res, label


def process_one_dataset(dataset_file: str, output_prefix: str = "processed") -> None:
    """Process a single TFRecord file.
    Performs the following:
    - reads and decodes the data
    - normalizes all the image data in all bands to be in [0,1]
    - adds additional derived features
    - serializes the data back to disk

    Args:
        dataset_file (str): The file to process
        output_prefix (str, optional): Prefix to add the name. Defaults to "processed".
    """
    # Read the data and decode it
    # Also normalize and remove blanks
    raw_dataset = read_raw_tfrecord(dataset_file)
    # Add the extra features if desired
    updated_dataset = raw_dataset.map(add_derived_features)
    # Write the data back to disk for use
    dataset_dir = os.path.dirname(dataset_file)
    dataset_name = os.path.basename(dataset_file)
    out_name = os.path.join(dataset_dir, f"{output_prefix}_{dataset_name}")

    write_processed_output(updated_dataset, out_name)


def compute_hash(file_name: str) -> str:
    """Compute the md5sum of the given file

    Args:
        file_name (str): The name of the file to process

    Returns:
        str: The hex representation of the hash
    """
    with open(file_name, "rb") as f:
        data = f.read()
        hash = hashlib.md5(data).hexdigest()
    return hash


def _process_data(flist: List[str], db_path: str) -> None:
    """Process all the TFRecord files in file list.
    Will:
    - Store the hash of all files for future reference
    - Process all the data as described in process_one_dataset

    Args:
        flist (List[str]): List of files to process
        db_path (str): Path to the json file in which to store the hashes
    """
    res = {}
    for f in track(flist):
        name = os.path.basename(f)
        res[name] = compute_hash(f)
        logger.info(f"Processing {f}")
        # process_one_dataset(f)
    with open(db_path, "w") as fw:
        json.dump(res, fw, indent=4)


def process_data(
    data_path: str,
    prefix: str = "part",
    dbname: str = "data_hashes.json",
    check_processed: bool = True,
) -> None:
    """Process an entire folder of TFRecords.

    Args:
        data_path (str): The path to the directory containing TFRecords
        prefix (str, optional): The prefix of the TFRecord files. Defaults to "part".
        dbname (str, optional): The name used to store file hashes. Defaults to "data_hashes.json".
        check_processed (bool, optional): Check if the data has been processed
            and if so, don't reprocess it. Defaults to True.
    """

    flist = glob.glob(os.path.join(data_path, f"{prefix}*"))
    db_path = os.path.join(data_path, dbname)

    if check_processed:
        # Check if we have already processed the data.
        # If not, process it
        if not os.path.isfile(db_path):
            # If there is no hashes file we know we haven't processed data yet
            logger.info("The hash record doesn't exist, will process the data")
            _process_data(flist, db_path)

        else:
            # We have a hashes file, check the data hasn't changed
            logger.info("Found existing hash record!")
            with open(db_path, "r") as fp:
                hashes = json.load(fp)
                retrain = False
                for name, hash in track(
                    hashes.items(),
                    description="Checking hashes correspond to current data",
                ):
                    current_md5 = compute_hash(os.path.join(data_path, name))
                    if current_md5 != hash:
                        logger.warning(
                            f"The hashes for {name} don't match we need to retrain!"
                        )
                        retrain = True
                if retrain:
                    # We have to retrain
                    logger.info("Processing the data, this may take some time")
                    _process_data(flist, db_path)
                else:
                    logger.info(
                        "Hashes correspond to the current data, will not re-process data"
                    )
    else:
        # We want to force data processing
        _process_data(flist, db_path)
