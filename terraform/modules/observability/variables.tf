variable "cluster_name" {
  type        = string
  description = "The name of the EKS cluster"
}

variable "log_group_name" {
  type        = string
  description = "The application log group name"
}

variable "aws_region" {
  type        = string
  description = "The AWS region"
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to resources"
  default     = {}
}
