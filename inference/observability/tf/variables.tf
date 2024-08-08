
variable "db_name" {
  type        = string
  description = "The name of the main inference pipeline database"
}


# The credentials for the database. We make them sensitive so
# they are never output by default
variable "db_username" {
  type        = string
  description = "The default user to make"
  sensitive   = true
}
variable "db_password" {
  type        = string
  description = "Password for the default user"
  sensitive   = true
}
