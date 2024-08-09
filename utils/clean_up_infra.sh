#!/bin/bash

origdir=$(pwd)
# Clean up the AWS resources **not** provisioned by terraform
# This is: the s3_model_registry_bucket and the ECR repository
# For this we have to parse the config again
echo "Cleaning up AWS resources not provisioned with terraform"
cd utils
python ./clean_up_inference_infra.py
cd $origdir

# Clean up the local grafana instance. Since this was local
# we can just nuke everything without running a terraform destroy
echo "Cleaning up local grafana resources"
cd inference/observability
docker compose down
rm tf/*.tfstate*
rm -rf tf/*.terraform*
cd $origdir

# Clean up the AWS resources provisioned by terraform
pwd
cd inference/setup/tf


printf '=%.0s' {1..80}
echo
echo "Cleaning up AWS resources provisioned with terraform"
echo "This may take up to 30 minutes"
printf '=%.0s' {1..80}
sleep 2
terraform destroy -var-file ./vars/droughtwatch.tfvars
echo
echo "Clean up complete. Double check you AWS resources on the AWS CloudConsole!"