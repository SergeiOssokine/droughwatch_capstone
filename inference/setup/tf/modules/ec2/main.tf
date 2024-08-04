# EC2 jumpbox, aka bastion host, to access RDS db
# from local machine

# The PUBLIC ssh key to access the jump box
resource "aws_key_pair" "bastion_key" {
  key_name   = "bastion-key"
  public_key = file("${path.module}/${var.bastion_key}")
}

# The OS we will run on the jump box
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

# The EC2 instance
resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.bastion_key.key_name
  associate_public_ip_address = false # No public IP
  iam_instance_profile        = aws_iam_instance_profile.bastion_profile.id
  subnet_id = var.private_subnet_id
  tags = {
    Name = "bastion"
  }
  security_groups = var.security_group_ids
}




output "network_interface_id" {
  value = aws_instance.bastion.primary_network_interface_id
}