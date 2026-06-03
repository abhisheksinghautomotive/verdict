output "vpc_id" {
  type        = string
  description = "The ID of the VPC"
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  type        = list(string)
  description = "List of public subnet IDs"
  value       = [for s in aws_subnet.public : s.id]
}

output "private_subnet_ids" {
  type        = list(string)
  description = "List of private subnet IDs"
  value       = [for s in aws_subnet.private : s.id]
}

output "node_security_group_id" {
  type        = string
  description = "The ID of the security group for EKS nodes"
  value       = aws_security_group.eks_nodes.id
}

output "alb_security_group_id" {
  type        = string
  description = "The ID of the security group for the ALB"
  value       = aws_security_group.alb.id
}

