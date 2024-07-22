#!/bin/bash
echo "Launching baseline training. This may take some time, especially to preprocess the data"
# Trigger the appropriate dag
curl -X POST 'localhost:8080/api/v1/dags/baseline/dagRuns' -H 'Content-Type: application/json' --user "admin:admin" -d '{}'
