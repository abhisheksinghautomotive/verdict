# 002. OIDC for GitHub Actions with Scoped Trust Policy

Date: 2026-06-04
Status: Accepted

## Context
The CI/CD pipeline needs to build Docker images, push them to Amazon ECR, deploy Helm charts to Amazon EKS, and provision infrastructure using Terraform. Using static, long-lived AWS credentials (like IAM access keys) inside GitHub Secrets introduces serious security risks such as credential leakage, lack of rotation, and overly broad account access. We need a secure, keyless authentication mechanism to authorize GitHub Actions workflows.

## Decision
We configure OpenID Connect (OIDC) identity federation between GitHub Actions and AWS IAM:
1. Establish a trust relationship between AWS IAM and the GitHub OIDC identity provider (`token.actions.githubusercontent.com`).
2. Create an IAM role `gha-verdict-deploy` in the bootstrap Terraform stack.
3. Restrict role assumption via OIDC trust policy conditions using:
   - `StringEquals` for `token.actions.githubusercontent.com:aud` = `sts.amazonaws.com`
   - `StringLike` for `token.actions.githubusercontent.com:sub` = `repo:abhisheksinghautomotive/verdict:*` (restricting access strictly to this specific repository).
4. Assign the AWS managed `AdministratorAccess` policy to the `gha-verdict-deploy` role. This is required because the role is used by the infrastructure deployment pipeline (`deploy-infrastructure.yml`) to provision, update, and destroy low-level networking resources (VPC, subnets, route tables, gateway, security groups), EKS clusters, and IAM configurations.
5. In the `dev` environment, define an EKS Access Entry to map the `gha-verdict-deploy` role to the cluster's administrators, granting it Kubernetes API access for Helm chart installation.

## Consequences
- **Keyless Security**: No long-lived AWS keys are stored in GitHub Secrets. Workflows use short-lived, auto-rotating credentials.
- **Repository Scoping**: Access is strictly limited to the `abhisheksinghautomotive/verdict` repository. No other repository can assume this role.
- **Administrative Privileges**: The role possesses administrative permissions. While broad, this is necessary for infrastructure-as-code deployment pipelines and is safely bounded by the OIDC repository trust condition.

## Cost impact
- $0 (AWS IAM OIDC and identity providers are free).
