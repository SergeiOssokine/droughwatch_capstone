resource "aws_lambda_function" "inference_lambda" {
  function_name = var.lambda_function_name
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
  vpc_config {
    subnet_ids = var.subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

resource "aws_security_group" "lambda_sg" {
  name        = "lambda-security-group_${var.lambda_function_name}"
  description = "Security group for Lambda function"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  timeouts {
    delete = "40m"
  }
}

# Return the arn of the created lambda
output "lambda_arn" {
  value = aws_lambda_function.inference_lambda.arn
}

# Return the lambda security group id
output "lambda_sg_group_id" {
  value = aws_security_group.lambda_sg.id
}