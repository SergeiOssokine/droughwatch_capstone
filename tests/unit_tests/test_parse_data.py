import os

from deepdiff import DeepDiff

from training.airflow.includes.parse_data import read_raw_tfrecord

mpath = os.path.dirname(__file__)

raw_record = os.path.join(
    mpath, "../integration_test_inference_pipeline/sample_data/28_07_24/part-r-00012"
)


def test_parse_raw_record():
    res = read_raw_tfrecord(raw_record)
    result = list(res.element_spec[0].keys())
    expected = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
    assert len(res.element_spec) == 2
    assert not DeepDiff(result, expected)
    print(res.element_spec[0]["B1"].shape)
    for key in expected:
        assert res.element_spec[0][key].shape == (65, 65, 1)
