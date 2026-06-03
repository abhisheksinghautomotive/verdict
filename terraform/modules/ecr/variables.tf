variable "repository_name" {
  type        = string
  description = "The name of the ECR repository"

  validation {
    condition     = length(var.repository_name) > 0 && can(regex("^[a-z0-9-_/]+$", var.repository_name))
    error_message = "The repository_name must be a non-empty string containing only lowercase alphanumeric characters, hyphens, underscores, and forward slashes."
  }
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to all resources"
  default     = {}
}
