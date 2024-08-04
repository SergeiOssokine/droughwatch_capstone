variable "db_name" {
  type        = string
  description = "The name of the database"
}
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
variable "vpc_security_group_ids" {
  type        = list(string)
  description = "The list of security group ids"
}
variable "db_subnet_group_name" {
  type        = string
  description = "The db subnet"
}
variable "vpc_id" {
  type = string
  description = "The VPC id"
}