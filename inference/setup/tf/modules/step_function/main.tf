resource "aws_sfn_state_machine" "sfn_state_machine" {
  name     = var.pipeline_name
  role_arn = aws_iam_role.StateMachineRole.arn
  definition = templatefile("${path.module}/pipeline/statemachine.asl.json", {
    ProcessingLambda = var.lambda_arns["processing"],
    InferenceLambda  = var.lambda_arns["inference"],
    ObserveLambda    = var.lambda_arns["observe"]
    }
  )

}


# Create a Log group for the state machine
resource "aws_cloudwatch_log_group" "MySFNLogGroup" {
  name_prefix       = "/aws/vendedlogs/states/MyStateMachine-"
  retention_in_days = 7
}

output "pipeline_arn" {
  value = aws_sfn_state_machine.sfn_state_machine.arn
}