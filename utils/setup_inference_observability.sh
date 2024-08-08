#!/bin/bash
cd inference/observability
echo "Launching Grafana instance"
docker compose up -d
cd tf
echo "Provisioning dashboard"
terraform init
terraform apply
echo "All done, point your browser to http://localhost:3000"

