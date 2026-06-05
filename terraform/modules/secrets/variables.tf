variable "secret_name" {
  type        = string
  description = "The name of the Secrets Manager secret"
}

variable "kms_key_alias" {
  type        = string
  description = "The alias for the customer-managed KMS key"
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to all resources"
  default     = {}
}
