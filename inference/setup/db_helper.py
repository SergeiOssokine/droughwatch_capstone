"""
This module contains various helper scripts for accessing and manipulating a
postgres database.
"""

import json
from collections import namedtuple
from typing import Dict

import boto3
import psycopg


def get_credentials(endpoint_url: str | None = None) -> Dict[str, str]:
    """Get the DB credentials from AWS secrets manager

    Args:
        endpoint_url (str | None, optional): The endpoint url to use. Defaults to None.

    Returns:
        Dict[str, str]: The DB secrets
    """
    if endpoint_url:
        sm = boto3.client("secretsmanager", endpoint_url=endpoint_url)
    else:
        sm = boto3.client("secretsmanager")
    response = sm.get_secret_value(SecretId="DB_CONN")
    db_config = json.loads(response["SecretString"])
    tmp_host, tmp_port = db_config["host"].split(":")
    db_config["host"] = tmp_host
    db_config["port"] = tmp_port

    return db_config


def prep_db(
    db_config: Dict[str, str], db_name: str, create_table_statement: str
) -> None:
    """Check if a database exists and if it does not, create it, along with the
    ledger table

    Args:
        db_config (Dict[str, str]): The db configuration
        db_name (str): Name of the database to create
        create_table_statement (str): The actual SQL statement to execute
    """
    host = db_config["host"]
    port = db_config["port"]
    user = db_config["username"]
    password = db_config["password"]
    with psycopg.connect(  # pylint: disable=E1129
        f"host={host} port={port} dbname=postgres user={user} password={password}",
        autocommit=True,
    ) as conn:
        res = conn.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        if len(res.fetchall()) == 0:
            conn.execute(f"create database {db_name};")
        with psycopg.connect(  # pylint: disable=E1129
            f"host={host} port={port} dbname={db_name} user={user} password={password}"
        ) as conn:
            conn.execute(create_table_statement)


SqlUpdate = namedtuple("SqlUpdate", ["field", "value"])


def update_table(
    table: str, db_name: str, update: SqlUpdate, cond: str, db_config: Dict[str, str]
) -> None:
    """Generate SQL code to update a certain column in a given table and database

    Args:
        table (str): The table to update
        db_name (str): The DB with the desired table
        update (_type_): The SqlUpdate object describing the update
        cond (str): The condition describing which rows to update
        db_config (Dict[str, str]): The DB config
    """

    sql_cmd = f"""
UPDATE {table}
SET {update.field} = '{update.value}'
WHERE {cond}
"""
    connection_string = (
        f"host={db_config['host']} "
        f"port={db_config['port']} "
        f"dbname={db_name} "
        f"user={db_config['username']} "
        f"password={db_config['password']}"
    )
    print(connection_string)
    with psycopg.connect(  # pylint: disable=E1129
        connection_string,
        autocommit=True,
    ) as conn:
        with conn.cursor() as curr:
            print(sql_cmd)
            curr.execute(sql_cmd)
