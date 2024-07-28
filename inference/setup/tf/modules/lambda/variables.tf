variable "model_bucket" {
  description = "Name of the bucket containing the model"
}
variable "data_bucket" {
  description = "Name of the bucket containing the data"
}

variable "lambda_function_name" {
  description = "Name of the lambda function"
}

variable "image_uri" {
  description = "ECR image uri"
}

variable "image_config_cmd"{
    description = "The cmd to use as the lambda handler"
}