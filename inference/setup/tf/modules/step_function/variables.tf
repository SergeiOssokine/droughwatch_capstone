variable "lambda_arns" {
  type        = map(string)
  description = "Dict of Lambda function ARNs that the step function can invoke"
}
variable "pipeline_name" {
  type        = string
  description = "The name of the pipeline"
}
