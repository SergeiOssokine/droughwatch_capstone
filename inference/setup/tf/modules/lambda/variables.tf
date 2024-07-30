variable "model_bucket" {
  type        = string
  description = "Name of the bucket containing the model"
}
variable "model_path" {
  type        = string
  description = "Name of the model to use"
}

variable "data_bucket" {
  type        = string
  description = "Name of the bucket containing the data"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the lambda function"
}

variable "image_uri" {
  type        = string
  description = "ECR image uri"
}

variable "image_config_cmd" {
  type        = string
  description = "The cmd to use as the lambda handler"
}
