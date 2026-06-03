variable "aws_region" {
  type        = string
  description = "The AWS region to deploy resources in"
  default     = "ap-south-1"

  validation {
    condition     = contains(["ap-south-1"], var.aws_region)
    error_message = "The verdict platform region must be ap-south-1."
  }
}
