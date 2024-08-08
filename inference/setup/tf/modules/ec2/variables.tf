variable "bastion_key" {
  type        = string
  description = "The PUBLIC ssh key to access the bastion EC2 instance. Only rsa and ed25519 allowed"
}

variable "private_subnet_id" {
  type        = string
  description = "The private subnet on which to sit"
}

variable "security_group_ids" {
  type        = list(string)
  description = "The security group ids"
}

variable "ecie_id" {
  type        = string
  description = "The ID of the endpoint the instance will be allowe to connect to"
}