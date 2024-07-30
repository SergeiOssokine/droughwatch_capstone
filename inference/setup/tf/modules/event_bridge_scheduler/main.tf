resource "aws_scheduler_schedule" "example" {
  name       = var.scheduler_name
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(${var.time_interval} hours)"

  target {
    arn      = var.pipeline_arn
    role_arn = aws_iam_role.iam_evbrige_scheduler.arn
    input = jsonencode({
      data_bucket_name = var.data_bucket
    })
  }
}
