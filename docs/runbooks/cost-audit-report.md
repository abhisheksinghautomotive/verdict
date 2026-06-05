# Cost Audit Report

- **Milestone**: Milestone 4
- **Issue**: Issue 32 (GitHub Issue #38)
- **Status**: Completed
- **Audited Date**: 2026-06-05

This report documents the final cost audit and resource cleanup of the Verdict platform.

---

## 1. Budget and Spend Summary

The Verdict project was designed to run within a **$100 lifetime/budget limit**. 

- **Audited Month-to-Date Spend**: $0.0000000115 USD (effectively $0.00)
- **Cumulative Project Spend (8 Weeks)**: ~$8.42 USD (well below the $20 target and $100 budget cap)
- **Active Running Cost**: ~$0.12/hour (when cluster is active)
- **At-Rest Idle Cost**: ~$0.05/month (S3 state storage only)

### AWS Cost Explorer Configuration
A monthly cost budget was configured with four alert thresholds (10%, 25%, 50%, 75%) linked via SNS alerts to the user's email. Budget alerts did not fire as total spend remained well below the thresholds.

---

## 2. Resource Orphan Audit

A comprehensive API audit was executed to ensure no active resources were left orphaned, which would otherwise incur ongoing charges.

| Service | Command Used | Active Resources | Status |
|---|---|---|---|
| **EKS** | `aws eks list-clusters` | None | Clear |
| **ECR** | `aws ecr describe-repositories` | None | Clear |
| **S3** | `aws s3 ls` | `verdict-tfstate-853095647398` (State Bucket) | Active (State) |
| **Secrets Manager** | `aws secretsmanager list-secrets` | None | Clear |
| **KMS** | `aws kms list-keys` | None (AWS-managed keys only) | Clear |
| **CloudWatch** | `aws logs describe-log-groups` | `/aws/application-signals/data` | Clear |
| **VPC & Net** | `aws ec2 describe-vpcs` | Default VPC only | Clear |
| **NAT Gateway** | `aws ec2 describe-nat-gateways` | None | Clear |
| **Elastic IP** | `aws ec2 describe-addresses` | None | Clear |
| **IAM** | `aws iam list-roles` | `gha-verdict-deploy` (Bootstrap role) | Active (Bootstrap) |

All dynamically provisioned compute and application resources were successfully destroyed, leaving only the minimal state management resources.

---

## 3. Retaining Bootstrap for Demos

The bootstrap resources include:
1. `gha-verdict-deploy` IAM Role: allows GitHub Actions workflows to authenticate via OIDC.
2. `verdict-tfstate-*` S3 Bucket: stores the remote Terraform state for environments.
3. `verdict-tflock` DynamoDB Table: manages lock status to prevent state corruption.
4. OIDC provider configuration.
5. SNS topic and AWS Budget alerts.

### Decision
**Keep bootstrap active.** 
- **Reason**: Retaining the bootstrap resources allows the playground environment to be cleanly spun up via `make up` and torn down via `make down` at a moment's notice.
- **Cost**: ~$0.05/month (S3 storage charges for the tfstate file). Zero active compute costs.
