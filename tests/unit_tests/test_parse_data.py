import os

from deepdiff import DeepDiff

from training.airflow.includes.parse_data import add_derived_features, read_raw_tfrecord

mpath = os.path.dirname(__file__)

raw_record = os.path.join(
    mpath, "../integration_test_inference_pipeline/sample_data/28_07_24/part-r-00012"
)


def test_parse_raw_record():
    """
    Test that parsing the raw TFRecord returns sensible results
    """
    res = read_raw_tfrecord(raw_record)
    result = list(res.element_spec[0].keys())
    expected = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
    # Check that the dataset is Tuple(Dict,TensorSpec)
    assert len(res.element_spec) == 2
    # Check that the arguments of the dict are as expected
    assert not DeepDiff(result, expected)
    # Check that the shape of every Tensor is correct
    for key in expected:
        assert res.element_spec[0][key].shape == (65, 65, 1)


def test_add_derived_features():
    raw_dataset = read_raw_tfrecord(raw_record)
    updated_dataset = raw_dataset.map(add_derived_features)
    assert len(updated_dataset.element_spec) == 2
    feats = updated_dataset.element_spec[0].keys()
    for feature in ['NDVI', 'NDMI', 'EVI']:
        assert feature in feats
