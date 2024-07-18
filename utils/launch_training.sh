#!/bin/bash

echo "Launching Docker container for training"
dr=$(pwd)
cd setup
if [ ! -f ".env" ]; then
    echo "Cannot find .env file in ./setup. This file is needed to configure the training docker container."
    exit 2
fi

rm ../training/airflow/*pid
docker compose up -d
echo "Done. Now point your browser to http://localhost:8080 to view the Airflow UI and launch the DAGs"
