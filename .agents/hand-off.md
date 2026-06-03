# Hand-off History

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
