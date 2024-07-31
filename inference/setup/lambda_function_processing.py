import json
import os
import tempfile
import traceback
from collections import namedtuple
from typing import List

import boto3
import pandas as pd
import psycopg
from db_helper import prep_db, sql_update, update_table
from parse_data import process_one_dataset

AWS_ENDPOINT_URL = os.getenv("aws_endpoint_url")
DROUGHTWATCH_DB = "droughtwatch"
LEDGER = "ledger"

create_table_statement = """
create table if not exists ledger(
	md5sum varchar(255) NOT NULL UNIQUE,
	path varchar(255),
    processed BOOLEAN DEFAULT FALSE,
    predictions_done BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""


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


def get_raw_data_names(bucket_name):
    s3 = boto3.resource("s3", endpoint_url=AWS_ENDPOINT_URL)
    # Get a list of all keys which we know are not products
    s3_bucket = s3.Bucket(bucket_name)
    names = [x.key for x in s3_bucket.objects.filter()]
    names = [x for x in names if ("processed" not in x) and ("parquet" not in x)]
    return names


def prep_ledger(db_config, key_list, bucket_name, forced: bool = False):
    fields = "md5sum, path"
    s3_resource = boto3.resource("s3", endpoint_url=AWS_ENDPOINT_URL)
    with psycopg.connect(
        f"host={db_config['host']} port=5432 dbname={DROUGHTWATCH_DB} user={db_config['username']} password={db_config['password']}",
        autocommit=True,
    ) as conn:
        df = pd.read_sql(f'select * from "{LEDGER}"', conn)
        if not forced:
            new_items = set(key_list) - set(df["path"].values)
        else:
            new_items = key_list
        for item in new_items:
            md5 = s3_resource.Object(bucket_name, item).e_tag.strip('"')
            sql_cmd = f"insert into {LEDGER} ({fields}) values (%s, %s)"
            values = [md5, item]
            with conn.cursor() as curr:
                curr.execute(sql_cmd, values)
    return new_items


def lambda_handler(event, context):

    try:
        sm = boto3.client("secretsmanager", endpoint_url=AWS_ENDPOINT_URL)
        response = sm.get_secret_value(SecretId="DB_CONN")
        db_config = json.loads(response["SecretString"])
        prep_db(db_config, DROUGHTWATCH_DB, create_table_statement)

        bucket_name = event["data_bucket_name"]
        if AWS_ENDPOINT_URL is not None:
            s3 = boto3.client("s3", endpoint_url=AWS_ENDPOINT_URL)
        else:
            s3 = boto3.client("s3")

        response = s3.list_objects_v2(
            Bucket=bucket_name,
        )

        # Add anything new to the DB

        names = get_raw_data_names(bucket_name)
        new_items = prep_ledger(db_config, names, bucket_name)

        # Loop over new stuff and process i
        for key in new_items:
            print(key)
            name = os.path.basename(key)
            base_dir = os.path.dirname(key)

            with tempfile.TemporaryDirectory() as tmpdirname:
                print("created temporary directory", tmpdirname)
                tmp_file = os.path.join(tmpdirname, name)
                with open(tmp_file, "w+b") as f:
                    s3.download_fileobj(bucket_name, key, f)

                processed_file = process_one_dataset(tmp_file, assign_id=True)
                with open(processed_file, "rb") as f:
                    s3.upload_fileobj(
                        f,
                        bucket_name,
                        os.path.join(base_dir, os.path.basename(processed_file)),
                    )
            # We managed to process things, let's update the ledger for corresponding item
            u = sql_update("processed", "TRUE")
            update_table("ledger", DROUGHTWATCH_DB, u, key, db_config)

        return {"statusCode": 200, "body": event}
    except Exception as e:
        tb_string = traceback.format_exc()
        print(tb_string)
        return {
            "statusCode": 500,
            "body": json.dumps({"Exception": str(e), "Traceback": tb_string}),
        }


if __name__ == "__main__":
    event = {
        "data_bucket_name": "droughtwatch-data",
    }
    lambda_handler(event, None)
