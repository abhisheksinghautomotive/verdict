# 003. IRSA Service Account for Pod Identity

Date: 2026-06-03
Status: Accepted

## Context
Pods running inside EKS need access to AWS ECR to pull images and AWS Secrets Manager to retrieve secrets. Using static AWS credentials or EC2 node instance profile permissions violates the principle of least privilege and introduces security risks, such as credentials leakage or unauthorized access across pods.

## Decision
We configure IAM Roles for Service Accounts (IRSA) for the verdict application pods:
1. Create a dedicated IAM Role (`verdict-app-irsa`) with a trust relationship restricted to the EKS cluster's OIDC identity provider and the specific Kubernetes ServiceAccount namespace and name (`system:serviceaccount:verdict:verdict-app`).
2. Attach a minimal policy allowing `secretsmanager:GetSecretValue` on verdict secret ARNs, ECR authentication, and `ecr:BatchGetImage` on the ECR repository ARN.
3. Annotate the Kubernetes ServiceAccount with `eks.amazonaws.com/role-arn` to instruct EKS to inject OIDC credentials dynamically at runtime.

## Consequences
- No long-lived or static AWS credentials are required in code or environment variables.
- Workloads conform to least-privilege principles by scoping access strictly to the verdict service account.
- Introduces dependency on EKS OIDC identity provider and AWS IAM components.

## Cost impact
- $0 (IAM and EKS OIDC providers are free of charge).
