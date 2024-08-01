import json
import os
import tempfile
import traceback

import boto3
import pandas as pd
import psycopg
from db_helper import get_credentials, prep_db, sql_update, update_table
from parse_data import process_one_dataset

AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")
DROUGHTWATCH_DB = "droughtwatch"
LEDGER = "ledger"

CREATE_TABLE_STATEMENT = """
create table if not exists ledger(
	md5sum varchar(255) NOT NULL UNIQUE,
	raw_path varchar(255),
    processed_path varchar(255) DEFAULT NULL,
    predictions_path varchar(255) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""


def get_raw_data_names(bucket_name):
    s3 = boto3.resource("s3", endpoint_url=AWS_ENDPOINT_URL)
    # Get a list of all keys which we know are not products
    s3_bucket = s3.Bucket(bucket_name)
    names = [x.key for x in s3_bucket.objects.filter()]
    names = [x for x in names if ("processed" not in x) and ("parquet" not in x)]
    return names


def prep_ledger(db_config, key_list, bucket_name, forced: bool = False):
    fields = "md5sum, raw_path"
    s3_resource = boto3.resource("s3", endpoint_url=AWS_ENDPOINT_URL)
    with psycopg.connect(  # pylint: disable=E1129
        f"host={db_config['host']} port=5432 dbname={DROUGHTWATCH_DB} user={db_config['username']} password={db_config['password']}",
        autocommit=True,
    ) as conn:
        df = pd.read_sql(f'select * from "{LEDGER}"', conn)
        if not forced:
            new_items = set(key_list) - set(df["raw_path"].values)
        else:
            new_items = key_list
        for item in new_items:
            md5 = s3_resource.Object(bucket_name, item).e_tag.strip('"')
            sql_cmd = f"insert into {LEDGER} ({fields}) values (%s, %s)"
            values = [md5, item]
            with conn.cursor() as curr:
                curr.execute(sql_cmd, values)
    return new_items


def lambda_handler(event, context):  # pylint: disable=unused-argument
    try:
        db_config = get_credentials(endpoint_url=AWS_ENDPOINT_URL)
        prep_db(db_config, DROUGHTWATCH_DB, CREATE_TABLE_STATEMENT)

        bucket_name = event["data_bucket_name"]
        if AWS_ENDPOINT_URL is not None:
            s3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
        else:
            s3 = boto3.client("s3")

        # Add anything new to the DB
        names = get_raw_data_names(bucket_name)
        new_items = prep_ledger(db_config, names, bucket_name)

        # Loop over new stuff and process it
        for key in new_items:

            name = os.path.basename(key)
            base_dir = os.path.dirname(key)

            with tempfile.TemporaryDirectory() as tmpdirname:
                # Get the original dataset
                tmp_file = os.path.join(tmpdirname, name)
                with open(tmp_file, "w+b") as f:
                    s3.download_fileobj(bucket_name, key, f)

                # This will create a processed file inside the temp directory
                processed_file = process_one_dataset(tmp_file, assign_id=True)
                processed_path = os.path.join(
                    base_dir, os.path.basename(processed_file)
                )
                # Save the processed file to the S3 bucket
                with open(processed_file, "rb") as f:
                    s3.upload_fileobj(
                        f,
                        bucket_name,
                        processed_path,
                    )

            # We managed to process things, let's update the ledger for corresponding item
            u = sql_update("processed_path", processed_path)
            cond = f"raw_path = '{key}'"
            update_table("ledger", DROUGHTWATCH_DB, u, cond, db_config)

        return {"statusCode": 200, "body": event}
    except Exception as e:  # pylint: disable=W0718
        tb_string = traceback.format_exc()
        print(tb_string)
        return {
            "statusCode": 500,
            "body": json.dumps({"Exception": str(e), "Traceback": tb_string}),
        }


if __name__ == "__main__":
    fake_event = {
        "data_bucket_name": "droughtwatch-data",
    }
    lambda_handler(fake_event, None)
