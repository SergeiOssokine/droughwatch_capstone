# Make sure to create state bucket beforehand
terraform {
  required_version = ">= 1.0"

}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current_identity" {}

locals {
  account_id = data.aws_caller_identity.current_identity.account_id
}






# Create a secrets manager to store database credentials
# Note that we set the recovery window to 0 days
# so that when terraform destroy is run, the secret is
# destroyed immediately
resource "aws_secretsmanager_secret" "DB_CONN" {
  name                    = "DB_CONN"
  description             = "Secrets for database connection"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.DB_CONN.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = module.inference_db.db_info["hostname"]
  })
}

# Use the default VPC
data "aws_vpc" "default" {
  default = true
}

# We need 2 private subnets in 2 AZs for the RDS instance
resource "aws_subnet" "db_subnet" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = "172.31.100.0/26" # 6 bits of IPs available
  availability_zone = "us-east-1f"

  tags = {
    Name = "Private DB Subnet"
  }
}


resource "aws_subnet" "db_subnet_2" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = "172.31.120.0/26" # 6 bits of IPs available
  availability_zone = "us-east-1b"

  tags = {
    Name = "Private DB Subnet 2"
  }
}


resource "aws_db_subnet_group" "default" {
  name       = "main"
  subnet_ids = [aws_subnet.db_subnet.id, aws_subnet.db_subnet_2.id]

  tags = {
    Name = "My DB subnet group"
  }
}

# The bastion host
module "bastion-host" {
  source            = "./modules/ec2"
  bastion_key       = var.bastion_key
  private_subnet_id = aws_subnet.db_subnet.id
  security_group_ids = [aws_security_group.bastion_sg.id]
  ecie_id = aws_ec2_instance_connect_endpoint.example.arn
}

# Processing lambda
module "processing_lambda_function" {
  source               = "./modules/lambda"
  image_uri            = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.lambda_image_name}"
  lambda_function_name = var.processing_lambda_function_name
  model_bucket         = var.model_bucket
  data_bucket          = var.data_bucket
  model_path           = var.model_path
  image_config_cmd     = var.processing_image_config_cmd
  secrets_arn          = aws_secretsmanager_secret.DB_CONN.arn
  subnet_ids           = [aws_subnet.db_subnet.id, aws_subnet.db_subnet_2.id]
  vpc_id               = data.aws_vpc.default.id
}


# Inference lambda
module "inference_lambda_function" {
  source               = "./modules/lambda"
  image_uri            = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.lambda_image_name}"
  lambda_function_name = var.inference_lambda_function_name
  model_bucket         = var.model_bucket
  model_path           = var.model_path
  data_bucket          = var.data_bucket
  image_config_cmd     = var.inference_image_config_cmd
  secrets_arn          = aws_secretsmanager_secret.DB_CONN.arn
  subnet_ids           = [aws_subnet.db_subnet.id, aws_subnet.db_subnet_2.id]
  vpc_id               = data.aws_vpc.default.id
}

# Observe lambda
module "observe_lambda_function" {
  source               = "./modules/lambda"
  image_uri            = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.lambda_image_name}"
  lambda_function_name = var.observe_lambda_function_name
  model_bucket         = var.model_bucket
  model_path           = var.model_path
  data_bucket          = var.data_bucket
  image_config_cmd     = var.observe_image_config_cmd
  secrets_arn          = aws_secretsmanager_secret.DB_CONN.arn
  subnet_ids           = [aws_subnet.db_subnet.id, aws_subnet.db_subnet_2.id]
  vpc_id               = data.aws_vpc.default.id
}


# Collect the ARN so we can pass them to the step function
# These are returned by each lambda module
locals {
  lambda_arns = {
    processing = module.processing_lambda_function.lambda_arn
    inference  = module.inference_lambda_function.lambda_arn
    observe    = module.observe_lambda_function.lambda_arn
  }
  lambda_sg_ids = [module.processing_lambda_function.lambda_sg_group_id, module.inference_lambda_function.lambda_sg_group_id, module.observe_lambda_function.lambda_sg_group_id]
}

# The main pipeline, built as a StepFunction state machine
# Uses the 3 lambdas above to do everything
module "inference_pipeline" {
  source        = "./modules/step_function"
  lambda_arns   = local.lambda_arns
  pipeline_name = var.pipeline_name
}

locals {
  pipeline_arn = module.inference_pipeline.pipeline_arn
}

# An EventBridge trigger that runs the pipeline every 24 hours
module "schduler_trigger" {
  source         = "./modules/event_bridge_scheduler"
  pipeline_arn   = local.pipeline_arn
  data_bucket    = var.data_bucket
  scheduler_name = var.scheduler_name
  time_interval  = var.time_interval
}

# RDS Postgres database
module "inference_db" {
  source                 = "./modules/rds"
  db_name                = var.db_name
  db_username            = var.db_username
  db_password            = var.db_password
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.default.name
}

# Route table we need for the S3 vpc endpoint
resource "aws_route_table" "private" {
  vpc_id = data.aws_vpc.default.id

  tags = {
    Name = "Private Route Table"
  }
}


resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.db_subnet.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.db_subnet_2.id
  route_table_id = aws_route_table.private.id
}


# VPC endpoint for s3
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"

  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"
}

# VPC endpoint for the secrets manager
# Note that it is of type interface so incurs costs
resource "aws_vpc_endpoint" "sm" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"

  private_dns_enabled = true
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.db_subnet.id, aws_subnet.db_subnet_2.id]
  security_group_ids  = [aws_security_group.secrets_manager_endpoint_sg.id]
}

# Set restrictive rules on the security group for sm
resource "aws_security_group" "secrets_manager_endpoint_sg" {
  name        = "secrets-manager-endpoint-sg"
  description = "Security group for Secrets Manager VPC Endpoint"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "HTTPS from Lambda"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = local.lambda_sg_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "Secrets Manager Endpoint Security Group"
  }
}
data "aws_region" "current" {}





# Bucket where new data should be added
# We set force_destroy to true so the bucket
# can be destroyed by terraform even when there is
# data in it
resource "aws_s3_bucket" "new_data_bucket" {
  bucket        = var.data_bucket
  force_destroy = true
}

# Enable s3 notifications on the bucket
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket      = aws_s3_bucket.new_data_bucket.id
  eventbridge = true
}


# Bation <-> RDS connection rules
# This is needed to allow 2-way communication between bastion
# host and the RDS

# Security group for the EC2 bastion instance
resource "aws_security_group" "bastion_sg" {
  name        = "bastion-sg"
  description = "Security group for bastion host"
  vpc_id      = data.aws_vpc.default.id
}

# Allow ssh access from the eic endpoint only
resource "aws_vpc_security_group_ingress_rule" "ec2_ssh_ingress" {
  security_group_id = aws_security_group.bastion_sg.id
  from_port   = 22
  ip_protocol = "tcp"
  to_port     = 22
  referenced_security_group_id = aws_security_group.eic_sg.id
  description = "Allows SSH access to bastion only from EIC endpoint"
}
 # Allow all outbound traffic
resource "aws_vpc_security_group_egress_rule" "ec2_ssh_egress" {
  security_group_id = aws_security_group.bastion_sg.id
  from_port   = 0
  ip_protocol = "-1"
  to_port     = 0
  cidr_ipv4 = "0.0.0.0/0"
  description = "Allows bastion to connect anywhere within the subnet"
}

resource "aws_security_group" "eic_sg" {
  name        = "eic-sg"
  description = "Security group for EC2 Instance Connect Endpoint"
  vpc_id      = data.aws_vpc.default.id
  # Only outbound rules are needed
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ec2_instance_connect_endpoint" "example" {
  subnet_id          = aws_subnet.db_subnet.id  # Place this in a private subnet
  security_group_ids = [aws_security_group.eic_sg.id]

  tags = {
    Name = "EC2 Instance Connect Endpoint"
  }
}



resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Security group for RDS"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_postgres_access" {
  count = length(local.lambda_sg_ids)

  security_group_id = aws_security_group.rds_sg.id

  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = local.lambda_sg_ids[count.index]
  description = "Allows lambda to connect to RDS for postgres"
}


# Inbound rule for RDS security group
resource "aws_vpc_security_group_ingress_rule" "rds_inbound" {
  from_port                = 5432
  to_port                  = 5432
  ip_protocol                 = "tcp"
  referenced_security_group_id = aws_security_group.bastion_sg.id
  security_group_id        = aws_security_group.rds_sg.id

  description = "Allows bastion to connect to RDS for postgres"
}



# Outbound rule for EC2 security group
resource "aws_vpc_security_group_egress_rule" "ec2_outbound" {
  from_port                = 5432
  to_port                  = 5432
  ip_protocol                 = "tcp"
  referenced_security_group_id = aws_security_group.rds_sg.id
  security_group_id        = aws_security_group.bastion_sg.id

  description = "Allows RDS to connect to bastion host for postgres"
}
