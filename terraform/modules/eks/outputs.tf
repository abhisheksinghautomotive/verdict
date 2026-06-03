output "cluster_endpoint" {
  description = "The endpoint for the EKS Kubernetes API server"
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_name" {
  description = "The name of the EKS cluster"
  value       = aws_eks_cluster.this.name
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider for IRSA"
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "oidc_provider_url" {
  description = "The OIDC Provider URL"
  value       = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "node_group_arn" {
  description = "The ARN of the EKS Managed Node Group"
  value       = aws_eks_node_group.this.arn
}

