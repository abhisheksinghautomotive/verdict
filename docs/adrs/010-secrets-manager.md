# 010. Migrate Application Secrets to AWS Secrets Manager
Date: 2026-06-05
Status: Accepted

## Context
Verdict application secrets must be secured to comply with security requirements (no secrets in code, images, environment variables, ConfigMaps, or Terraform state). They must be fetched dynamically at startup by application containers using short-lived AWS IAM credentials mapped via EKS IAM Roles for Service Accounts (IRSA).

## Decision
We will:
1. Create a customer-managed KMS key to encrypt sensitive Secrets Manager secrets.
2. Provision an AWS Secrets Manager secret named `verdict/app/api-key` using the KMS key for encryption.
3. Update the IRSA module to grant `secretsmanager:GetSecretValue` on the secret ARN and `kms:Decrypt` on the customer-managed KMS key ARN to the `verdict-app-irsa` role.
4. Update the Helm deployment to inject `VERDICT_SECRET_ID` and `AWS_REGION` environment variables.
5. Update `app/main.py` to initialize the boto3 Secrets Manager client on startup and retrieve the secret string dynamically.
6. Enforce a `recovery_window_in_days = 0` (force delete) on the Secrets Manager secret and a `deletion_window_in_days = 7` on the KMS key to support quick teardown and avoid lingering costs in development.

## Consequences
- Plain-text secrets are removed from version control and environment configurations.
- The pod is granted restricted read-only access to Secrets Manager and KMS decrypt functions at runtime.
- EKS pods must run under an IAM role configured with IRSA.
- AWS Secrets Manager and KMS keys will incur minimal at-rest costs in development when the stack is persistent.

## Cost Impact
- Customer-managed KMS key: $1.00/month at rest (prorated hourly).
- Secrets Manager secret: $0.40/month per secret.
- Total at-rest cost increase: $1.40/month.
