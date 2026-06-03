output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "node_security_group_id" {
  description = "The ID of the security group for EKS nodes"
  value       = module.vpc.node_security_group_id
}

output "alb_security_group_id" {
  description = "The ID of the security group for the ALB"
  value       = module.vpc.alb_security_group_id
}

output "cluster_endpoint" {
  description = "The endpoint for the EKS Kubernetes API server"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "The name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider for IRSA"
  value       = module.eks.oidc_provider_arn
}

output "oidc_provider_url" {
  description = "The OIDC Provider URL"
  value       = module.eks.oidc_provider_url
}


