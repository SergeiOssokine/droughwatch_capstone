# The basic trust policy for an EC2 instance
resource "aws_iam_role" "bastion_role" {
  name = "bastion_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}



resource "aws_iam_policy" "ec2_connect_policy" {
  name        = "ec2_connect_policy_bastion"
  description = "IAM Policy for connecting to an EC2 isntance connect endpoint"
  policy = <<EOF
{
	"Version": "2012-10-17",
    "Statement": [{
            "Sid": "EC2InstanceConnect",
            "Action": "ec2-instance-connect:OpenTunnel",
            "Effect": "Allow",
            "Resource": "${var.ecie_id}",
            "Condition": {
                "NumericEquals": {
                    "ec2-instance-connect:remotePort": "22"
                },
                "NumericLessThanEquals": {
                    "ec2-instance-connect:maxTunnelDuration": "36000"
                }
            }
        },
        {
            "Sid": "SSHPublicKey",
            "Effect": "Allow",
            "Action": "ec2-instance-connect:SendSSHPublicKey",
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "ec2:osuser": "ubuntu"
                }
            }
        },
        {
            "Sid": "Describe",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceConnectEndpoints"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
  EOF
}
resource "aws_iam_role_policy_attachment" "iam-policy-attach" {
  role       = aws_iam_role.bastion_role.name
  policy_arn = aws_iam_policy.ec2_connect_policy.arn
}


# Create profile so the right role is associated with the EC2 instance
resource "aws_iam_instance_profile" "bastion_profile" {
  name = "bastion_profile"
  role = aws_iam_role.bastion_role.name
}
