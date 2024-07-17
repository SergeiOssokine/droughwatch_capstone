#!/bin/bash

echo "Setting up the environment with uv"
uv venv .mlops
source .mlops/bin/activate
echo "Installing dev packages"
uv pip install -r setup/dev_requirements.txt
echo "Installing pre-commit"
pre-commit install
python -c "import requests"
echo "Now activate the environment by running source .mlops/bin/activate"
