# Teardown and Cleanup Runbook

This runbook documents the steps to safely tear down the Dev/Prod environments and outlines the manual verification required to ensure zero orphan resources and clean state cycles.

## Teardown Checklist

Always follow this order when tearing down the environment:

1. **Helm Release Teardown**
   - Uninstall the Helm release to release any Kubernetes resources (ServiceAccount, Pods, Services, etc.):
     ```bash
     helm uninstall verdict-app -n verdict
     ```

2. **Terraform Infrastructure Destroy**
   - Navigate to the environment directory (e.g. `terraform/environments/dev/`) and destroy all resources:
     ```bash
     terraform destroy -auto-approve
     ```

3. **Orphan Verification**
   - Run the AWS CLI queries below to check for any orphan VPC resources.

## AWS CLI Cleanup Verification Queries

To guarantee that no orphan resource is left running (especially VPCs, Subnets, EIPs, Internet Gateways, Route Tables, or Security Groups), run these commands:

```bash
# Verify VPC is deleted (should return empty list [])
aws ec2 describe-vpcs --filters Name=tag:Project,Values=verdict --query "Vpcs[].VpcId"

# Verify Subnets are deleted (should return empty list [])
aws ec2 describe-subnets --filters Name=tag:Project,Values=verdict --query "Subnets[].SubnetId"

# Verify Security Groups are deleted (should return empty list [])
aws ec2 describe-security-groups --filters Name=tag:Project,Values=verdict --query "SecurityGroups[].GroupId"

# Verify Internet Gateways are deleted (should return empty list [])
aws ec2 describe-internet-gateways --filters Name=tag:Project,Values=verdict --query "InternetGateways[].InternetGatewayId"

# Verify Route Tables are deleted (should return empty list [])
aws ec2 describe-route-tables --filters Name=tag:Project,Values=verdict --query "RouteTables[].RouteTableId"
```

## Destroy & Re-apply Cycle Validation Results

A full destroy and re-apply cycle was executed successfully in the `dev` environment on 2026-06-03.

### Cycle 1 (First Apply)
The following resources were successfully provisioned:
- **VPC**: `vpc-03dfb1cecf6a5716b`
- **Subnet (Public)**: `subnet-07d0b1a046502be8d`
- **Internet Gateway**: `igw-0e54e57a79d2ba365`
- **Route Table (Public)**: `rtb-043ef34ecb8db6d73`
- **Security Group (EKS Nodes)**: `sg-01fe70b9e30d0f3ef`
- **Security Group (ALB)**: `sg-0b609b182fa685074`

### Cycle 2 (Destroy & Verify Orphans)
- Run: `terraform destroy -auto-approve`
- Outcome: Destroyed 14 resources cleanly.
- Verification queries:
  - VPCs: `[]`
  - Subnets: `[]`
  - Security Groups: `[]`
  - Internet Gateways: `[]`
  - Route Tables: `[]`
- Result: **0 resources leaked/orphaned**.

### Cycle 3 (Re-apply)
- Run: `terraform apply -auto-approve`
- Outcome: Created 14 resources cleanly.
- New Resource IDs:
  - **VPC**: `vpc-0731894774f241a7b`
  - **Subnet (Public)**: `subnet-0c7961d474f76932c`
  - **Internet Gateway**: `igw-0f6b49b5475cd0585`
  - **Route Table (Public)**: `rtb-04b8872dae7848956`
  - **Security Group (EKS Nodes)**: `sg-0b20381163908a5cf`
  - **Security Group (ALB)**: `sg-0990ad2ee1fa4125f`
- Run: `terraform plan`
- Result: `No changes. Your infrastructure matches the configuration.`
