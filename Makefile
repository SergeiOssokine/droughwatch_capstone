SHELL:=/bin/bash

setup_env:
	bash ./utils/setup_env.sh

download_data:
	python ./utils/download_data.py

build_training:
	@( \
		echo "Building the training image"; \
		cd setup; \
		docker build . -t droughtwatch_training \
	)

launch_training_infra: build_training
	bash ./utils/launch_training.sh

train_baseline:
	bash ./training/scripts/launch_baseline.sh
