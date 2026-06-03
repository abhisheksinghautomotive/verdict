# Hand-off History

---

## Issue 14: Configure managed node group with t3.small SPOT for dev

### Status
- **Completed Issue**: GitHub Issue #14 (`Issue 9` in `milestones.md`)
- **Git Branch**: `feat/issue-14-eks-node-group`

### What Was Completed
1. **Configured Node Group Variables**: Parameterized node scaling (desired: 1, min: 1, max: 2), capacity type (default `SPOT`), and instance types (default `["t3.small"]`) in `terraform/modules/eks/variables.tf` with validation rules.
2. **Worker Node IAM Role & Policy Attachments**: Created IAM role `aws_iam_role.node` with policies `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, and `AmazonEC2ContainerRegistryReadOnly` attached.
3. **EKS Managed Node Group**: Provisioned `aws_eks_node_group.this` inside EKS module pointing to the custom IAM role and placement subnet (first public subnet).
4. **Outputs Configuration**: Exposed `node_group_arn` from EKS module.
5. **Validation and Linting**:
   - Formatted all files with `terraform fmt -recursive`.
   - Verified syntactic validity with `terraform validate`.
   - Verified execution plan via `terraform plan` showing 25 resources to add (incorporating the 5 EKS node/IAM resources).

### Next Steps
- Implement **Milestone 2 Issue 10**: Create ECR repository with scan-on-push and image lifecycle.

---

## Issue 13: Write Terraform module for EKS cluster

### Status
- **Completed Issue**: GitHub Issue #13 (`Issue 8` in `milestones.md`)
- **Git Branch**: `feat/issue-13-eks-module`

### What Was Completed
1. **Created EKS Module**: Added a reusable EKS module under `terraform/modules/eks/` with `main.tf`, `variables.tf`, `outputs.tf`, and `versions.tf`.
2. **Cluster IAM Role & Policy**: Configured the cluster service role and attached the `AmazonEKSClusterPolicy` managed policy.
3. **EKS Cluster Control Plane**: Provisioned the `aws_eks_cluster` resource in the configured subnets with private/public endpoint access.
4. **OIDC Provider for IRSA**: Configured the TLS certificate data source and provisioned the `aws_iam_openid_connect_provider` pointing to the cluster's OIDC issuer URL.
5. **VPC AZ Extension**: Updated the development environment to deploy public subnets across two AZs (`ap-south-1a` and `ap-south-1b`) as required by EKS HA Control Plane, while node placement remains pinned to the first AZ to maintain the cost-saving single-AZ model.
6. **Validation and Linting**:
   - Verified that the code adheres to style rules using `terraform fmt -recursive`.
   - Verified syntactic and provider configuration validity using `terraform validate`.
   - Run `terraform plan` to verify the execution plan, resulting in 20 resources planned to be added (16 VPC/networking and 4 EKS).

### Next Steps
- Implement **Milestone 2 Issue 9**: Configure managed node group with t3.small SPOT for dev.

---

## Issue 12: Write Makefile with up / down / nuke / cost targets

### Status
- **Completed Issue**: GitHub Issue #12 (`Issue 7a` in `milestones.md`)
- **Git Branch**: `feat/issue-12-makefile`

### What Was Completed
1. **Created Root Makefile**: Added a root-level `Makefile` with targets `bootstrap`, `up`, `down`, `nuke`, `cost`, and `help`.
2. **Interactive Bootstrap Support**: Configured `bootstrap` to pass the optional `ALERT_EMAIL` variable to avoid prompting in non-interactive setups.
3. **Robust Environment Hooks**: Configured `up` and `down` to perform Terraform operations and conditionally run Helm commands only if the Helm chart directories exist, ensuring smooth progression through future milestones.
4. **Clean Nuke Confirmation**: Configured `nuke` to prompt for confirmation and supply a dummy `alert_email` variable to allow non-interactive destroy of bootstrap resources.
5. **Dynamic Cost Queries**: Implemented portable date calculations via Python to fetch current-month Cost Explorer metrics in the `cost` target.
6. **Documentation**: Created implementation plan, task list, and walkthrough tracking artifacts.

### Next Steps
- Implement **Milestone 2 Issue 8**: Write Terraform module for EKS cluster.

---


## Issue 11: Validate full destroy and re-apply cycle works cleanly

### Status
- **Completed Issue**: GitHub Issue #11 (`Issue 7` in `milestones.md`)
- **Git Branch**: `feat/issue-11-destroy-apply-validation`

### What Was Completed
1. **Executed Full Apply**: Verified successful provision of 14 VPC and networking resources in the `dev` environment on AWS (`ap-south-1`).
2. **Executed Full Teardown**: Successfully destroyed all 14 resources using `terraform destroy`.
3. **Orphan Verification**: Programmatically queried AWS using the AWS CLI and confirmed that 0 resources (VPCs, subnets, route tables, internet gateways, security groups) were left orphaned.
4. **Verified Recreation Cycle**: Re-applied the Terraform configuration cleanly (another 14 resources added) and confirmed that a subsequent `terraform plan` returned a zero-diff state (`No changes`).
5. **Documented Runbook**: Created the teardown runbook and documented the cycle validation results in [teardown-checklist.md](file:///Users/abhisheksingh/Desktop/verdict/docs/runbooks/teardown-checklist.md).
6. **Clean State Check**: Ran `terraform destroy` at the end of validation to leave the AWS playground completely clean and cost-free.

### Next Steps
- Implement **Issue 7a**: Write Makefile with up / down / nuke / cost targets.

---

## Issue 10: Package VPC as a clean Terraform module

### Status
- **Completed Issue**: GitHub Issue #10 (`Issue 6` in `milestones.md`)
- **Git Branch**: `feat/issue-10-vpc-module`

### What Was Completed
1. **Module Separation Verified**: Verified that all VPC infrastructure resources (VPC, subnets, IGW, NAT GW, EIP, route tables, and associations) are fully contained within the reusable `terraform/modules/vpc/` module.
2. **Security Groups Included**: Confirmed that the node and ALB security groups, as well as their rules, are located within the VPC module (`terraform/modules/vpc/security_groups.tf`).
3. **Module Inputs & Outputs Configured**: Verified that the VPC module variables (in `variables.tf`) have descriptions, types, and defaults, and the five required outputs (`vpc_id`, `public_subnet_ids`, `private_subnet_ids`, `node_security_group_id`, `alb_security_group_id`) are correctly exposed.
4. **Dev Environment Integration**: Verified that the dev environment (`terraform/environments/dev/main.tf`) consumes the VPC module via a single `module "vpc"` block referencing `../../modules/vpc`.
5. **Validation & Planning**:
   - Validated syntax using `terraform validate` inside `terraform/environments/dev/`.
   - Confirmed code is fully formatted using `terraform fmt -recursive`.
   - Verified that `terraform plan` successfully plans the creation of all 14 dev-footprint resources.

### Next Steps
- Implement **Issue 7**: Validate full destroy and re-apply cycle.

---

## Issue 9: Define security groups for EKS nodes and ALB

### Status
- **Completed Issue**: GitHub Issue #9 (`Issue 5` in `milestones.md`)
- **Git Branch**: `feat/issue-9-security-groups`

### What Was Completed
1. **Created Security Groups file**: Added `terraform/modules/vpc/security_groups.tf` containing all security groups and rules.
2. **Configured Node Security Group**: Created `aws_security_group.eks_nodes` for worker nodes. Added rules to allow ingress from self (all ports/protocols), ingress from the ALB security group on TCP port range `1025-65535`, and egress to all (`0.0.0.0/0` on all protocols).
3. **Configured ALB Security Group**: Created `aws_security_group.alb` for the application load balancer. Added rules to allow HTTP (port 80) and HTTPS (port 443) ingress from `0.0.0.0/0`, and egress limited strictly to the node security group on TCP port range `1025-65535`.
4. **Exposed Outputs**: Added `node_security_group_id` and `alb_security_group_id` to both the VPC module `outputs.tf` and the root dev environment `outputs.tf`.
5. **Validation & Planning**:
   - Initialized and validated using `terraform init` and `terraform validate`.
   - Verified that `terraform plan` shows exactly 8 new resources to be added (the 2 security groups and 6 security group rules).
   - Formatted all code using `terraform fmt -recursive`.

### Next Steps
- Implement **Issue 6**: Package VPC as a clean Terraform module.

---

## Issue 8: Create route tables for public and private subnets

### Status
- **Completed Issue**: GitHub Issue #8 (`Issue 4` in `milestones.md`)
- **Git Branch**: `feat/issue-8-route-tables`

### What Was Completed
1. **Created public route table and route**: Always created `aws_route_table.public` and an `aws_route` for `0.0.0.0/0` pointing to the Internet Gateway.
2. **Associated public subnets**: Associated all public subnets with the public route table using `aws_route_table_association.public`.
3. **Conditional private route table**: Gated `aws_route_table.private` behind `var.enable_private_subnets`.
4. **Conditional private NAT route**: Gated `aws_route.private_nat_gateway` behind `var.enable_private_subnets && var.enable_nat` to route to the NAT Gateway when enabled.
5. **Associated private subnets**: Associated private subnets dynamically to the private route table when private subnets exist.
6. **Validation & Planning**:
   - Formatted all files with `terraform fmt -recursive`.
   - Validated syntax with `terraform validate`.
   - Tested dev mode plan (6 resources added, no private or NAT resources).
   - Tested prod mode plan (12 resources added, private subnets, NAT Gateway, EIP, private route tables, routes, and associations all proposed correctly).

### Next Steps
- Implement **Issue 5**: Define security groups for EKS nodes and ALB.

---

## Issue 7: Configure Internet Gateway and conditional NAT Gateway

### Status
- **Completed Issue**: GitHub Issue #7 (`Issue 3` in `milestones.md`)
- **Git Branch**: `feat/issue-7-internet-nat-gateway`

### What Was Completed
1. **Configured Internet Gateway**: Always created `aws_internet_gateway` inside the VPC module, attached to the VPC.
2. **Configured Conditional NAT Gateway**: Gated `aws_eip` and `aws_nat_gateway` behind the `enable_nat` boolean variable using `count = var.enable_nat ? 1 : 0`.
3. **Subnet Placement**: Placed the NAT Gateway in the first public subnet dynamically via `aws_subnet.public[var.availability_zones[0]].id`.
4. **Validation and Formatting**:
   - Validated syntax using `terraform validate`.
   - Verified that running `terraform plan` with `enable_nat = false` provisions 3 resources (VPC, public subnet, Internet Gateway) and 0 private/NAT resources.
   - Verified that running `terraform plan` with `enable_nat = true` provisions 5 resources (adding Elastic IP and NAT Gateway).
   - Formatted all code using `terraform fmt -recursive`.

### Next Steps
- Implement **Issue 8**: Create route tables for public and private subnets.

---

## Issue 6: Provision VPC with configurable AZs and subnet topology

### Status
- **Completed Issue**: GitHub Issue #6 (`Issue 2` in `milestones.md`)
- **Git Branch**: `feat/issue-6-vpc-topology`

### What Was Completed
1. **Created a reusable VPC module** under `terraform/modules/vpc/`:
   - `variables.tf`: Parameterized VPC `cidr_block` (default `10.0.0.0/16`), `availability_zones` (list, restricted to 1-3 valid zones in `ap-south-1` via validation), `enable_private_subnets`, `enable_nat` (forward compatibility), and `common_tags`.
   - `main.tf`: Provisions `aws_vpc` with DNS resolution, `aws_subnet.public` dynamically with EKS tags, and `aws_subnet.private` conditionally. Subnet CIDRs are offset dynamically to prevent overlap.
   - `outputs.tf`: Outputs `vpc_id`, `public_subnet_ids`, and `private_subnet_ids`.
2. **Integrated VPC module into the dev environment**:
   - `terraform/environments/dev/variables.tf`: Region parameter with validation.
   - `terraform/environments/dev/main.tf`: Instantiated `vpc` module with single AZ `ap-south-1a`, public subnets only.
   - `terraform/environments/dev/outputs.tf`: Forwards VPC and subnet outputs.
   - `terraform/environments/dev/providers.tf` & `versions.tf`: Binds to AWS provider `>= 5.0` and regional provider config.
3. **Validated formatting and syntax**:
   - Formatted files via `terraform fmt -recursive`.
   - Initialized and validated dev environment using `terraform init` and `terraform validate`.
   - Verified the execution plan via `terraform plan` showing 2 additions (VPC, public subnet) and 0 private subnets.

### Next Steps
- Implement **Issue 3**: Configure Internet Gateway and conditional NAT Gateway.

---

## Issue 5: Create AWS Budget with $10 / $25 / $50 / $75 SNS alerts

### Status
- **Completed Issue**: GitHub Issue #5 (`Issue 1a` in `milestones.md`)
- **Git Branch**: `feat/issue-5-aws-budget`

### What Was Completed
1. **Created a budget module** under `terraform/modules/budget/`:
   - `variables.tf`: Parameterized `alert_email` (with regex validation) and `common_tags`.
   - `main.tf`: Provisions the SNS topic `verdict-budget-alerts`, the SNS email subscription, the SNS topic policy allowing `budgets.amazonaws.com` to publish, and the monthly $100 budget with four actual cost alerts (10%, 25%, 50%, 75%).
   - `outputs.tf`: Outputs `sns_topic_arn`.
2. **Integrated the module into the bootstrap workspace**:
   - `terraform/bootstrap/main.tf`: Instantiates the budget module using local tags.
   - `terraform/bootstrap/variables.tf`: Exposes the required `alert_email` variable (no default to prevent committing sensitive emails).
   - `terraform/bootstrap/outputs.tf`: Outputs the `sns_topic_arn`.
3. **Validated formatting and syntax**:
   - Formatted files via `terraform fmt -recursive`.
   - Initialized and validated using `terraform init` and `terraform validate`.
   - Verified the execution plan via `terraform plan` showing 4 additions (SNS topic, SNS subscription, SNS policy, AWS budget).

### Next Steps
- Implement **Issue 2**: Provision VPC with configurable AZs and subnet topology.

---

## Issue 4: Create S3 remote state and DynamoDB lock

### Status
- **Completed Issue**: GitHub Issue #4 (`Issue 1` in `milestones.md`)
- **Git Branch**: `feat/issue-4-tf-remote-state`

### What Was Completed
1. **Installed Terraform v1.15.5** via Homebrew (`hashicorp/tap/terraform`).
2. **Updated `.gitignore`** to ignore Terraform-specific binaries, state files, and variables.
3. **Created `terraform/bootstrap/` files**:
   - `versions.tf`: Pinned Terraform `>= 1.5.0` and AWS provider `~> 5.0`.
   - `providers.tf`: Binds to the specified AWS region.
   - `variables.tf`: Parameterized and validated the region (`ap-south-1`).
   - `main.tf`: Provisions S3 bucket (`verdict-tfstate-853095647398`) with encryption, versioning, and public block, and DynamoDB table (`verdict-tflock`) with proper tagging.
   - `outputs.tf`: Outputs S3 bucket and DynamoDB table name.
4. **Deployed bootstrap infrastructure**: Ran `terraform apply` locally. Created resources successfully.
5. **Configured Dev Environment Backend**:
   - Created `terraform/environments/dev/backend.tf` with a partial backend configuration to avoid committing sensitive account IDs or regions.
   - Generated the gitignored `backend.tfvars` locally and tested dev backend initialization (`terraform init -backend-config=backend.tfvars`). It initialized successfully.
