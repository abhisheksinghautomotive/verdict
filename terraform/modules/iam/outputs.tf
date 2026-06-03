output "role_arn" {
  description = "The ARN of the verdict-app-irsa IAM role"
  value       = aws_iam_role.verdict_app.arn
}
