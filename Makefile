SHELL:=/bin/bash

setup_env:
	bash ./utils/setup_env.sh

download_data:
	python ./utils/download_data.py


setup_training_infra:
	bash ./utils/setup_training_infra.sh

launch_training_infra:
	bash ./utils/launch_training_infra.sh

train_baseline:
	bash ./training/scripts/launch_baseline.sh

clean_up_training:
	@( \
		cd training/setup && docker compose down \
	)

integration_tests:
	bash ./tests/integration_test_inference_pipeline/integration_tests.sh