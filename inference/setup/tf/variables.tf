variable "aws_region" {
  description = "AWS region to create resources"
  default     = "us-east-1"
  type        = string
}

variable "project_id" {
  description = "project_id"
  default     = "mlops-zoomcamp"
  type        = string
}



variable "model_bucket" {
  description = "s3 bucket where model lives"
  type        = string
}

variable "model_path" {
  description = "Name of the model to use"
  type        = string
}

variable "data_bucket" {
  description = "s3 bucket where data lives"
  type        = string
}


variable "processing_lambda_function_name" {
  description = "The lambda function that will transform raw data to processed data for inference"
  type        = string
}

variable "inference_lambda_function_name" {
  description = "The lambda function that will run inference on the processed data to produce predictions"
  type        = string
}

variable "observe_lambda_function_name" {
  description = "The lambda function that will run inference on the processed data to produce predictions"
  type        = string
}


variable "processing_image_config_cmd" {
  description = "The override cmd to specify the processing lambda handler inside the image"
  type        = string
}

variable "inference_image_config_cmd" {
  description = "The override cmd to specify the inference lambda handler inside the image"
  type        = string
}

variable "observe_image_config_cmd" {
  description = "The override cmd to specify the observe lambda handler inside the image"
  type        = string
}


variable "lambda_image_name" {
  description = "The name of the image which will be used to run the inference pipeline"
  type        = string
}

variable "pipeline_name" {
  description = "The name of the inference pipeline"
  type        = string
}

variable "scheduler_name" {
  description = "The name of the EventBridge scheduler"
  type        = string
}

variable "time_interval" {
  type        = number
  description = "The scheduler will trigger the pipeline every this many hours"
}

variable "db_name" {
  type        = string
  description = "The name of the main inference pipeline database"
}
# The credentials for the database. We make them sensitive so
# they are never output by default
variable "db_username" {
  type        = string
  description = "The default user to make"
  sensitive   = true
}
variable "db_password" {
  type        = string
  description = "Password for the default user"
  sensitive   = true
}


variable "bastion_key" {
  type = string
  description = "The PUBLIC ssh key to access the bastion EC2 instance. Only rsa and ed25519 allowed"
}