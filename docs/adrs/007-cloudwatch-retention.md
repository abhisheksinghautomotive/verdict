# 007. CloudWatch Container Insights Retention

Date: 2026-06-04
Status: Accepted

## Context

We need observability into our EKS worker nodes and application pods to monitor performance metrics (CPU, Memory) and collect logs. Amazon CloudWatch Container Insights provides automated metrics collection, but log and metric ingestion costs can quickly build up if not carefully managed. By default, AWS-created CloudWatch log groups have infinite retention, which leads to high storage costs over time. 

For our hobbyist budget ($100 lifetime), we must minimize storage costs while retaining enough troubleshooting data during development.

## Decision

We will:
1. Install the official `amazon-cloudwatch-observability` EKS Add-On via the `aws_eks_addon` Terraform resource.
2. Pre-create the required CloudWatch log groups in Terraform:
   - `/aws/containerinsights/verdict-dev/application`
   - `/aws/containerinsights/verdict-dev/dataplane`
   - `/aws/containerinsights/verdict-dev/host`
3. Parameterize the log retention period:
   - Dev environment: `container_insights_retention_days = 1` (1 day).
   - Prod environment: `container_insights_retention_days = 7` (7 days).
4. Configure an IAM Role for Service Accounts (IRSA) named `verdict-cloudwatch-observability-irsa` to trust the `cloudwatch-agent` and `fluent-bit` service accounts in the `amazon-cloudwatch` namespace. This role will have the AWS managed policy `CloudWatchAgentServerPolicy` attached.

## Consequences

- Pre-creating the log groups ensures they are created with the desired retention policy before the addon starts, preventing automatic creation with infinite retention.
- Node and pod metrics will be successfully forwarded to CloudWatch.
- Log storage costs are capped to 1 day of usage in the dev environment.

## Cost impact

- Dev log storage cost is reduced to near-zero (~$0.01/month).
- Ingestion costs remain low due to the small footprint of a single-node spot cluster.
