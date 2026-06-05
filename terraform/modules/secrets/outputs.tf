output "secret_arn" {
  description = "The ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secret.arn
}

output "secret_name" {
  description = "The name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.app_secret.name
}

output "kms_key_arn" {
  description = "The ARN of the customer-managed KMS key"
  value       = aws_kms_key.secrets.arn
}
