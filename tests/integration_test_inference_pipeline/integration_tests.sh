#!/bin/bash
echo "Building the image with lambda functions"
curdir=$(pwd)
docker build --build-arg="PREFIX=inference/setup" -f inference/setup/Dockerfile -t inference:v0.1 .
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