variable "aws_region" {
  type        = string
  description = "The AWS region to deploy resources in"
  default     = "ap-south-1"

  validation {
    condition     = contains(["ap-south-1"], var.aws_region)
    error_message = "The verdict platform region must be ap-south-1."
  }
}

variable "alert_email" {
  type        = string
  description = "The email address to receive budget alerts"

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "The alert_email must be a valid email address."
  }
}

