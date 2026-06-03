output "role_arn" {
  description = "The ARN of the verdict-app-irsa IAM role"
  value       = aws_iam_role.verdict_app.arn
}

output "alb_controller_role_arn" {
  description = "The ARN of the aws-load-balancer-controller IAM role (IRSA)"
  value       = aws_iam_role.aws_load_balancer_controller.arn
}

