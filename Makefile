SHELL:=/bin/bash
# Self-documenting Makefile, taken from
# https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html

setup_env: ## Set up the local environment by installing the required Python packages
	bash ./utils/setup_env.sh

download_data: ## Download the training and validation data
	python ./utils/download_data.py


setup_training_infra: ## Set up the training infrastructure (configures everything)
	bash ./utils/setup_training_infra.sh

launch_training_infra: ## Launch the training infrastrcture (launches the Docker pipeline)
	bash ./utils/launch_training_infra.sh

train_baseline: ## Launch the training of the baseline model  (vai a POST request to Airflow)
	bash ./training/scripts/launch_baseline.sh

clean_up_training: ## Bring down the training infrastructure containers
	@( \
		cd training/setup && docker compose down \
	)

setup_inference_infra: ## Set up the inference infra (configure, build main docker image and push to ECR)
	python ./utils/prepare_inference_infrastructure.py

provision_inference_infra: ## Use terraform to provision the inference infrastucture on AWS
	bash ./utils/provision_inference_infra.sh

setup_inference_observability: ## Use Docker + terraform to provision a local Grafana instance with a metrics dashboard, connected to AWS
	bash ./utils/setup_inference_observability.sh

upload_and_run_inference: ## Upload a bunch of new data to S3 and run the inference pipeline on it
	python ./inference/emulation/add_new_data.py

integration_tests: ## Run the integration test on the lambda functions
	bash ./tests/integration_test_inference_pipeline/integration_tests.sh


.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help