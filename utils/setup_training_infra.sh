#!/bin/bash


python ./utils/prepare_training_infrastructure.py


echo "Launching the docker compose stack"
cd setup
docker compose up -d
echo "Done. Now point your browser to http://localhost:8080 to view the Airflow UI"
