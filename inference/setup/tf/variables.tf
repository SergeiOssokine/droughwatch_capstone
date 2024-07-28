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


variable "processing_image_config_cmd"{
    description = "The override cmd to specify the processing lambda handler inside the image"
    type=string
}

variable "inference_image_config_cmd"{
    description = "The override cmd to specify the inference lambda handler inside the image"
    type=string
}