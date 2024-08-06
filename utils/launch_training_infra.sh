#!/bin/bash
echo "Launching the docker compose stack"
docker compose -f training/setup/docker-compose.yml up -d
echo "Done. Now point your browser to http://localhost:8080 to view the Airflow UI"
