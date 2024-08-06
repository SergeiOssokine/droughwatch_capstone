#!/bin/bash
docker build --build-arg="PREFIX=training/setup" -f training/setup/Dockerfile  . -t droughtwatch_training
python ./utils/prepare_training_infrastructure.py
