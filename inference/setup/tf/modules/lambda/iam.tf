resource "aws_iam_role" "iam_lambda" {
  name               = "iam_${var.lambda_function_name}"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
          ]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}


# IAM for S3

resource "aws_iam_policy" "lambda_s3_role_policy" {
  name        = "lambda_s3_policy_${var.lambda_function_name}"
  description = "IAM Policy for s3"
  policy = <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"s3:Get*",
				"s3:List*",
                "s3:Put*"
			],
			"Resource": [
				"arn:aws:s3:::${var.model_bucket}",
				"arn:aws:s3:::${var.model_bucket}/*",
                "arn:aws:s3:::${var.data_bucket}",
				"arn:aws:s3:::${var.data_bucket}/*"
			]
		}
	]
}
  EOF
}

resource "aws_iam_role_policy_attachment" "iam-policy-attach" {
  role       = aws_iam_role.iam_lambda.name
  policy_arn = aws_iam_policy.lambda_s3_role_policy.arn
}

data "aws_iam_policy" "allow_cloudwatch" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "allow_cloudwatch_at" {
  role       = aws_iam_role.iam_lambda.name
  policy_arn = data.aws_iam_policy.allow_cloudwatch.arn
}