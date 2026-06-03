variable "cidr_block" {
  type        = string
  description = "The CIDR block for the VPC"
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "The cidr_block must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  type        = list(string)
  description = "List of availability zones in ap-south-1 to deploy subnets in"

  validation {
    condition     = length(var.availability_zones) >= 1 && length(var.availability_zones) <= 3 && alltrue([for az in var.availability_zones : contains(["ap-south-1a", "ap-south-1b", "ap-south-1c"], az)])
    error_message = "availability_zones must contain 1 to 3 valid ap-south-1 availability zones (ap-south-1a, ap-south-1b, ap-south-1c)."
  }
}

variable "enable_private_subnets" {
  type        = bool
  description = "Whether to create private subnets"
  default     = false
}

variable "enable_nat" {
  type        = bool
  description = "Whether to enable NAT Gateway (forward compatibility for future issues)"
  default     = false
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to all resources"
  default     = {}
}
