"""
This module contains test of various functions  related to the
inference pipeline.
"""

import boto3
import pytest
from moto import mock_aws

from inference.setup.db_helper import get_credentials


@pytest.fixture
def sample_secret():  # pylint: disable=missing-function-docstring
    raw = """{"username": "postgres",
  "password": "mlops4thewin",
  "host": "localhost:5432"}"""
    return raw


@mock_aws
def test_get_credentials(sample_secret):
    """
    Test that the DB connection secret is recovered correctly
    """
    sm = boto3.client("secretsmanager")
    sm.create_secret(
        Name="DB_CONN",
        Description="Secret for connecting to DB",
        SecretString=sample_secret,
    )
    creds = get_credentials()

    assert creds["username"] == "postgres"
    assert creds["password"] == "mlops4thewin"
    assert creds["host"] == "localhost"
    assert creds["port"] == "5432"
