data "aws_caller_identity" "current" {}

resource "aws_kms_key" "secrets" {
  description             = "KMS customer-managed key for encrypting Verdict secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_kms_alias" "secrets" {
  name          = var.kms_key_alias
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_secretsmanager_secret" "app_secret" {
  name                    = var.secret_name
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 0

  tags = var.common_tags
}

resource "aws_secretsmanager_secret_version" "app_secret_val" {
  secret_id = aws_secretsmanager_secret.app_secret.id
  secret_string = jsonencode({
    api_key = "dummy-dev-api-key-value"
  })
}
