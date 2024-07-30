variable "scheduler_name" {
    type = string
    description = "The name to give to the time-based scheduler"
}
variable "pipeline_arn" {
  type = string
  description = "The arn of the step function pipeline"
}

variable "data_bucket" {
  description = "s3 bucket where data lives"
  type        = string
}

variable "time_interval" {
  type = number
  description = "The scheduler will trigger the pipeline every this many hours"
}