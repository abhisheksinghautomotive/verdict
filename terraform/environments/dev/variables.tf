variable "aws_region" {
  type        = string
  description = "The AWS region to deploy resources in"
  default     = "ap-south-1"

  validation {
    condition     = contains(["ap-south-1"], var.aws_region)
    error_message = "The verdict platform region must be ap-south-1."
  }
}

variable "container_insights_retention_days" {
  type        = number
  description = "Retention in days for CloudWatch Container Insights log groups"
  default     = 1

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653, 0], var.container_insights_retention_days)
    error_message = "The retention_in_days must be a valid CloudWatch retention period."
  }
}

