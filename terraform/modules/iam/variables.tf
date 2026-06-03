variable "oidc_provider_arn" {
  type        = string
  description = "The ARN of the EKS cluster OIDC provider"
}

variable "oidc_provider_url" {
  type        = string
  description = "The URL of the EKS cluster OIDC provider"
}

variable "ecr_repository_arn" {
  type        = string
  description = "The ARN of the ECR repository"
}

variable "secrets_manager_secret_arn" {
  type        = string
  description = "The ARN of the Secrets Manager secret. If null, a wildcard matching 'verdict' secrets in the current region/account will be used."
  default     = null
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to all resources"
  default     = {}
}
