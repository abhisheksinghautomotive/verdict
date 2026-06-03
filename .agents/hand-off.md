# Hand-off History

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
