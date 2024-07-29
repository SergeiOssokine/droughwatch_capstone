#!/bin/bash
echo "Launching localstack"
docker compose up -d
python ./integration_test.py

