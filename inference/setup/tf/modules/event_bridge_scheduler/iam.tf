resource "aws_iam_role" "iam_evbrige_scheduler" {
  name               = "iam_${var.scheduler_name}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "scheduler.amazonaws.com"
          ]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "evbridge_scheduler_role_policy" {
  name        = "evbridge_scheduler_policy_${var.scheduler_name}"
  description = "IAM Policy for scheduler to start StepFunction execution"
  policy      = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
        {
            "Effect": "Allow",
            "Action": [ "states:StartExecution" ],
            "Resource": [ "arn:aws:states:*:*:stateMachine:*" ]
        }
     ]
}
  EOF
}
