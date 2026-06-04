# 008. Nightly Teardown Workflow

Date: 2026-06-04
Status: Accepted

## Context

Running AWS EKS clusters and managed node groups is relatively expensive (EKS control plane is $0.10/hour, plus compute node costs). During development, it is easy to forget to run `make down` at the end of a session, leading to overnight or weekend resource leaks that quickly deplete the $100 lifetime project budget.

We need a automated safety net that guarantees any running EKS compute resource is destroyed at the end of each day.

## Decision

We will implement a scheduled GitHub Actions workflow (`.github/workflows/nightly-teardown.yml`) running every night at 23:00 IST (17:30 UTC / `30 17 * * *` cron).

The workflow will:
1. Authenticate to AWS using OIDC via the `gha-verdict-deploy` IAM role.
2. Check if the `verdict-dev` EKS cluster is currently running.
3. If the cluster is running, initialize Terraform in the dev environment and run `terraform destroy -target=module.eks -auto-approve`.

We will NOT target VPC or bootstrap resources (S3, DynamoDB, budgets) as they have negligible at-rest costs (~$1/month total) and should persist to maintain the workspace structure.

## Consequences

- If development resources are left active, they will be cleaned up automatically every night, capping maximum accidental spend for any single day to a few hours.
- If resources are destroyed by the nightly workflow, the developer will need to run `make up` to redeploy the environment before starting their next development session.
- Because `helm_release.aws_load_balancer_controller` and EKS access entries depend directly on the EKS module outputs, Terraform will automatically destroy them as part of the targeted EKS module destroy path. This leaves the VPC and ECR resources intact.

## Cost Impact

- Reduces the risk of runaway EKS control plane and worker node costs.
- Cost of running the GitHub Actions runner for the teardown is covered under GitHub's free tier.
