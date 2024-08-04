resource "aws_db_instance" "db" {
  identifier             = var.db_name
  instance_class         = "db.t3.micro"
  allocated_storage      = 10
  engine                 = "postgres"
  engine_version         = "16.3"
  username               = var.db_username
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  vpc_security_group_ids = var.vpc_security_group_ids
  db_subnet_group_name   = var.db_subnet_group_name
}



output "db_info" {
  value = {
    arn      = aws_db_instance.db.arn
    hostname = aws_db_instance.db.endpoint
  }
}
output "rds_instance_id" {
  value = aws_db_instance.db.id
}
