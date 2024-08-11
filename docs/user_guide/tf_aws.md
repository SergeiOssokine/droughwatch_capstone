## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.62.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_bastion-host"></a> [bastion-host](#module\_bastion-host) | ./modules/ec2 | n/a |
| <a name="module_inference_db"></a> [inference\_db](#module\_inference\_db) | ./modules/rds | n/a |
| <a name="module_inference_lambda_function"></a> [inference\_lambda\_function](#module\_inference\_lambda\_function) | ./modules/lambda | n/a |
| <a name="module_inference_pipeline"></a> [inference\_pipeline](#module\_inference\_pipeline) | ./modules/step_function | n/a |
| <a name="module_observe_lambda_function"></a> [observe\_lambda\_function](#module\_observe\_lambda\_function) | ./modules/lambda | n/a |
| <a name="module_processing_lambda_function"></a> [processing\_lambda\_function](#module\_processing\_lambda\_function) | ./modules/lambda | n/a |
| <a name="module_schduler_trigger"></a> [schduler\_trigger](#module\_schduler\_trigger) | ./modules/event_bridge_scheduler | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_db_subnet_group.default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_subnet_group) | resource |
| [aws_ec2_instance_connect_endpoint.example](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_instance_connect_endpoint) | resource |
| [aws_route_table.private](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table) | resource |
| [aws_route_table_association.private_1](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association) | resource |
| [aws_route_table_association.private_2](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association) | resource |
| [aws_s3_bucket.new_data_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket) | resource |
| [aws_s3_bucket_notification.bucket_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_notification) | resource |
| [aws_secretsmanager_secret.DB_CONN](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret) | resource |
| [aws_secretsmanager_secret_version.credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version) | resource |
| [aws_security_group.bastion_sg](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [aws_security_group.eic_sg](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [aws_security_group.rds_sg](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [aws_security_group.secrets_manager_endpoint_sg](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [aws_subnet.db_subnet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet) | resource |
| [aws_subnet.db_subnet_2](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet) | resource |
| [aws_vpc_endpoint.s3](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint) | resource |
| [aws_vpc_endpoint.sm](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint) | resource |
| [aws_vpc_security_group_egress_rule.ec2_outbound](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_egress_rule) | resource |
| [aws_vpc_security_group_egress_rule.ec2_ssh_egress](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_egress_rule) | resource |
| [aws_vpc_security_group_ingress_rule.ec2_ssh_ingress](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_ingress_rule) | resource |
| [aws_vpc_security_group_ingress_rule.rds_inbound](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_ingress_rule) | resource |
| [aws_vpc_security_group_ingress_rule.rds_postgres_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_ingress_rule) | resource |
| [aws_caller_identity.current_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [aws_vpc.default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region to create resources | `string` | `"us-east-1"` | no |
| <a name="input_bastion_key"></a> [bastion\_key](#input\_bastion\_key) | The PUBLIC ssh key to access the bastion EC2 instance. Only rsa and ed25519 allowed | `string` | n/a | yes |
| <a name="input_data_bucket"></a> [data\_bucket](#input\_data\_bucket) | s3 bucket where data lives | `string` | n/a | yes |
| <a name="input_db_name"></a> [db\_name](#input\_db\_name) | The name of the main inference pipeline database | `string` | n/a | yes |
| <a name="input_db_password"></a> [db\_password](#input\_db\_password) | Password for the default user | `string` | n/a | yes |
| <a name="input_db_username"></a> [db\_username](#input\_db\_username) | The default user to make | `string` | n/a | yes |
| <a name="input_inference_image_config_cmd"></a> [inference\_image\_config\_cmd](#input\_inference\_image\_config\_cmd) | The override cmd to specify the inference lambda handler inside the image | `string` | n/a | yes |
| <a name="input_inference_lambda_function_name"></a> [inference\_lambda\_function\_name](#input\_inference\_lambda\_function\_name) | The lambda function that will run inference on the processed data to produce predictions | `string` | n/a | yes |
| <a name="input_lambda_image_name"></a> [lambda\_image\_name](#input\_lambda\_image\_name) | The name of the image which will be used to run the inference pipeline | `string` | n/a | yes |
| <a name="input_model_bucket"></a> [model\_bucket](#input\_model\_bucket) | s3 bucket where model lives | `string` | n/a | yes |
| <a name="input_model_path"></a> [model\_path](#input\_model\_path) | Name of the model to use | `string` | n/a | yes |
| <a name="input_observe_image_config_cmd"></a> [observe\_image\_config\_cmd](#input\_observe\_image\_config\_cmd) | The override cmd to specify the observe lambda handler inside the image | `string` | n/a | yes |
| <a name="input_observe_lambda_function_name"></a> [observe\_lambda\_function\_name](#input\_observe\_lambda\_function\_name) | The lambda function that will run inference on the processed data to produce predictions | `string` | n/a | yes |
| <a name="input_pipeline_name"></a> [pipeline\_name](#input\_pipeline\_name) | The name of the inference pipeline | `string` | n/a | yes |
| <a name="input_processing_image_config_cmd"></a> [processing\_image\_config\_cmd](#input\_processing\_image\_config\_cmd) | The override cmd to specify the processing lambda handler inside the image | `string` | n/a | yes |
| <a name="input_processing_lambda_function_name"></a> [processing\_lambda\_function\_name](#input\_processing\_lambda\_function\_name) | The lambda function that will transform raw data to processed data for inference | `string` | n/a | yes |
| <a name="input_scheduler_name"></a> [scheduler\_name](#input\_scheduler\_name) | The name of the EventBridge scheduler | `string` | n/a | yes |
| <a name="input_time_interval"></a> [time\_interval](#input\_time\_interval) | The scheduler will trigger the pipeline every this many hours | `number` | n/a | yes |

## Outputs

No outputs.
