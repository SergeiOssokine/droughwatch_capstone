import json
from collections import namedtuple
from typing import Dict

import boto3
import psycopg


def get_credentials(endpoint_url: str | None = None) -> Dict[str, str]:
    if endpoint_url:
        sm = boto3.client("secretsmanager", endpoint_url=endpoint_url)
    else:
        sm = boto3.client("secretsmanager")
    response = sm.get_secret_value(SecretId="DB_CONN")
    db_config = json.loads(response["SecretString"])
    return db_config


def prep_db(db_config: Dict[str, str], db_name: str, create_table_statement: str):
    host = db_config["host"]
    user = db_config["username"]
    password = db_config["password"]
    with psycopg.connect(
        f"host={host} port=5432 user={user} password={password}", autocommit=True
    ) as conn:
        res = conn.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        if len(res.fetchall()) == 0:
            conn.execute(f"create database {db_name};")
        with psycopg.connect(
            f"host={host} port=5432 dbname={db_name} user={user} password={password}"
        ) as conn:
            # print(create_table_statement)
            conn.execute(create_table_statement)


def update_table(
    table: str, db_name: str, update, cond: str, db_config: Dict[str, str]
):
    sql_cmd = f"""
UPDATE {table}
SET {update.field} = '{update.value}'
WHERE {cond}
"""
    with psycopg.connect(
        f"host={db_config['host']} port=5432 dbname={db_name} user={db_config['username']} password={db_config['password']}",
        autocommit=True,
    ) as conn:
        with conn.cursor() as curr:
            print(sql_cmd)
            curr.execute(sql_cmd)


sql_update = namedtuple("sql_update", ["field", "value"])
