import datetime
import os
from collections import OrderedDict
from typing import Any, Dict, Union

import awswrangler as wr
import pandas as pd
import psycopg
from db_helper import get_credentials, prep_db
from evidently import ColumnMapping
from evidently.metrics import (
    ColumnDriftMetric,
    ColumnSummaryMetric,
    DatasetMissingValuesMetric,
)
from evidently.report import Report

AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")

DROUGHTWATCH_DB = "droughtwatch"
LEDGER = "ledger"
METRICS = "metrics"

CREATE_TABLE_STATEMENT = """
create table if not exists metrics(
    predictions_path varchar(255),
	timestamp timestamp,
	class_0_frac float,
    class_1_frac float,
    class_2_frac float,
    class_3_frac float,
    most_common_percentage float,
	share_missing_values float,
    prediction_drift float
)
"""
num_features = ["P_0", "P_1", "P_2", "P_3", "P_label"]
column_mapping = ColumnMapping(
    target=None, prediction="label", numerical_features=num_features
)


def insert_row_into_table(curr: psycopg.Cursor, row: Dict[str, Any], table_name: str):
    """Insert a given row into the PostgreSQL table

    Args:
        curr (psycopg.Cursor): The current cursor
        row (Dict[str, Any]): The row to insert
        table_name (str): The table into which to insert the row
    """
    ks = row.keys()
    fields = ", ".join(ks)
    values = [row[k] for k in ks]
    pls = ", ".join(["%s"] * len(ks))
    sql_cmd = f"insert into {table_name}({fields}) values ({pls})"
    curr.execute(sql_cmd, values)


def extract_metric_data(result: Dict[str, Any]) -> Dict[str, Union[int, float, str]]:
    """Extract the numbers relevant to each metric

    Args:
        result (Dict[str, Any]): The result dict from evidently

    Returns:
        Dict[str, Union[int, float, str]]: A dictionary of the metrics
    """
    result_metrics = OrderedDict()
    metrics = result["metrics"]

    result_metrics["share_missing_values"] = metrics[0]["result"]["current"][
        "share_of_missing_values"
    ]
    result_metrics["most_common_percentage"] = metrics[1]["result"][
        "current_characteristics"
    ]["most_common_percentage"]
    result_metrics["prediction_drift"] = metrics[2]["result"]["drift_score"]
    return result_metrics


def compute_metrics(current_data: pd.DataFrame, ref_data: pd.DataFrame):
    # Generate the report
    report = Report(
        metrics=[
            DatasetMissingValuesMetric(),
            ColumnSummaryMetric(column_name="label"),
            ColumnDriftMetric(column_name="label"),
        ]
    )
    report.run(
        reference_data=ref_data,
        current_data=current_data,
        column_mapping=column_mapping,
    )
    result = report.as_dict()
    metrics = extract_metric_data(result)

    props = current_data["label"].value_counts() / current_data["label"].count()
    # metrics.update(**{f"class_{k}_frac": v for k, v in props.to_dict().items()})
    metrics.update({f"class_{k}_frac": v for k, v in props.items()})
    metrics["timestamp"] = datetime.datetime.now()

    return metrics


def get_new_predictions(db_config):
    with psycopg.connect(  # pylint: disable=E1129
        f"host={db_config['host']} port={db_config['port']} dbname={DROUGHTWATCH_DB} user={db_config['username']} password={db_config['password']}",
        autocommit=True,
    ) as conn:
        df_ledger = pd.read_sql(f'select * from "{LEDGER}"', conn)
        df_metrics = pd.read_sql(f'select * from "{METRICS}"', conn)
        new_items = set(df_ledger["predictions_path"].values) - set(
            df_metrics["predictions_path"]
        )
        return new_items


def lambda_handler(event, context):
    ev = event["body"]
    bucket_name = ev["data_bucket_name"]

    if AWS_ENDPOINT_URL is not None:
        wr.config.s3_endpoint_url = AWS_ENDPOINT_URL

    reference_data_path = os.getenv("reference_path", "reference_data.parquet")
    db_config = get_credentials(endpoint_url=AWS_ENDPOINT_URL)

    # We get the unobserved cases

    prep_db(db_config, DROUGHTWATCH_DB, CREATE_TABLE_STATEMENT)
    host = db_config["host"]
    user = db_config["username"]
    port = db_config["port"]
    password = db_config["password"]
    predictions_list = get_new_predictions(db_config)
    with psycopg.connect(  # pylint: disable=E1129
        f"host={host} port={port} user={user} dbname={DROUGHTWATCH_DB} password={password}",
        autocommit=True,
    ) as conn:
        for prediction in predictions_list:
            # Compute the metrics we want
            df = wr.s3.read_parquet(path=f"s3://{bucket_name}/{prediction}")
            df_ref = wr.s3.read_parquet(
                path=f"s3://{bucket_name}/{reference_data_path}"
            )
            metrics = OrderedDict()
            metrics.update(predictions_path=prediction)
            metrics.update(**compute_metrics(df, df_ref))

            with conn.cursor() as curr:
                insert_row_into_table(curr, metrics, "metrics")
    return {"statusCode": 200, "body": "Updated observation table"}


if __name__ == "__main__":
    event = {
        "body": {"data_bucket_name": "droughtwatch-data"},
    }
    lambda_handler(event, None)
