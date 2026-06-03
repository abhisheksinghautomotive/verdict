variable "cluster_name" {
  type        = string
  description = "The name of the EKS cluster"

  validation {
    condition     = length(var.cluster_name) > 0 && can(regex("^[a-zA-Z0-9-_]+$", var.cluster_name))
    error_message = "The cluster_name must be a non-empty string containing only alphanumeric characters, hyphens, and underscores."
  }
}

variable "cluster_version" {
  type        = string
  description = "The Kubernetes version for the EKS cluster"
  default     = "1.30"

  validation {
    condition     = var.cluster_version == "1.30"
    error_message = "The cluster_version must be exactly 1.30 for the verdict platform."
  }
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for the EKS control plane. Must reside in at least two different Availability Zones."

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least two subnet IDs must be provided for the EKS cluster control plane to satisfy High Availability requirements."
  }
}

variable "node_subnet_placement" {
  type        = list(string)
  description = "List of subnet IDs where the worker nodes will be placed"

  validation {
    condition     = length(var.node_subnet_placement) >= 1
    error_message = "At least one subnet ID must be provided for node subnet placement."
  }
}

variable "node_security_group_id" {
  type        = string
  description = "The ID of the security group to associate with EKS nodes"

  validation {
    condition     = length(var.node_security_group_id) > 0 && startswith(var.node_security_group_id, "sg-")
    error_message = "The node_security_group_id must be a valid security group ID starting with 'sg-'."
  }
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags to apply to all resources"
  default     = {}
}
