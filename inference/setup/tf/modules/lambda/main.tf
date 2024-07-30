resource "aws_lambda_function" "inference_lambda" {
  function_name = var.lambda_function_name
  # This can also be any base image to bootstrap the lambda config, unrelated to your Inference service on ECR
  # which would be anyway updated regularly via a CI/CD pipeline
  image_uri    = var.image_uri # required-argument
  package_type = "Image"
  role         = aws_iam_role.iam_lambda.arn
  tracing_config {
    mode = "Active"
  }
  image_config {
    command = [ var.image_config_cmd ]
  }
  // This step is optional (environment)
  environment {
    variables = {
      "model_registry_s3_bucket": var.model_bucket,
      "model_path": var.model_path
    }
  }
  timeout     = 700
  memory_size = 3000
}

# Return the arn of the created lambda
output "lambda_arn" {
  value = aws_lambda_function.inference_lambda.arn
}