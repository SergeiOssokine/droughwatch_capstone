# Create an IAM role for the Step Functions state machine
data "aws_iam_policy_document" "state_machine_assume_role_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = [
      "sts:AssumeRole",
    ]
  }
}

resource "aws_iam_role" "StateMachineRole" {
  name               = "StepFunctions-Terraform-Role-${var.pipeline_name}"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role_policy.json
}


data "aws_iam_policy_document" "state_machine_role_policy" {

  statement {
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData",
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = values(var.lambda_arns)
  }

}

# Create an IAM policy for the Step Functions state machine
resource "aws_iam_role_policy" "StateMachinePolicy" {
  role   = aws_iam_role.StateMachineRole.id
  policy = data.aws_iam_policy_document.state_machine_role_policy.json
}
