#!/bin/bash
echo "Building the image with lambda functions"
curdir=$(pwd)
cd inference/setup
docker build -t inference:v0.1 .
cd $curdir
cd tests/integration_test_inference_pipeline/
echo "Launching localstack"
docker compose up  -d
sleep 3

python ./integration_test.py
ERROR_CODE=$?

if [ ${ERROR_CODE} != 0 ]; then
    docker compose down
    exit ${ERROR_CODE}
fi
docker compose down
cd $curdir