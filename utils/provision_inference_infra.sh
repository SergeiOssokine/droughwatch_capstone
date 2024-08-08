#!/bin/bash
cd inference/setup/tf
echo "Initializing terraform"
terraform init
echo "Privsioning infrastructure on AWS"
terraform apply -var-file ./vars/droughtwatch.tfvars
echo "Done"