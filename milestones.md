# Milestones and Issues

Four milestones, eight weeks. Each issue lists **Required** (the deliverable and why) and **How** (the concrete steps). Work them in order — later issues depend on earlier ones.

---

## Milestone Overview

| # | Milestone | Due | Issues |
|---|---|---|---|
| 1 | Foundation Infrastructure | Week 2 | 1, 1a, 2, 3, 4, 5, 6, 7, 7a |
| 2 | Container Platform | Week 4 | 8, 9, 10, 11, 12, 13, 14, 15, 16 |
| 3 | CI/CD Pipeline | Week 6 | 17, 18, 19, 20, 21, 22, 23, 24, 25, 25a |
| 4 | Observability and Security | Week 8 | 26, 27, 28, 29, 30, 31, 32 |

**Total:** 35 issues across 8 weeks (32 original + 3 added: Budget alarm, Makefile, Nightly teardown).

---

## Milestone 1 — Foundation Infrastructure

**Due:** Week 2
**Theme:** Stand up a safe, cheap AWS playground with cost guardrails and a reusable VPC module. Nothing expensive runs yet. By the end, `make up` and `make down` cycle cleanly without leaking resources.

---

### Issue 1: Create S3 bucket and DynamoDB table for Terraform remote state

**Required:** A versioned S3 bucket to store Terraform state files and a DynamoDB table for state locking. Without these, every `terraform apply` risks corrupting state if interrupted, and there is no audit history.

**How:**
- Create a one-time `terraform/bootstrap/` directory using local state (chicken-and-egg).
- Provision an S3 bucket with versioning, SSE-S3 encryption, public access fully blocked.
- Provision a DynamoDB table `verdict-tflock`, hash key `LockID` (string), billing `PAY_PER_REQUEST`.
- Configure `terraform/environments/dev/backend.tf` to use the bucket and table.
- Run `terraform init -migrate-state` to push local state to S3.

---

### Issue 1a: Create AWS Budget with $10 / $25 / $50 / $75 SNS alerts

**Required:** An AWS Budgets policy that emails you at four spend thresholds so runaway costs cannot exceed the $100 credit. This must exist before any chargeable resource is provisioned.

**How:**
- Create SNS topic `verdict-budget-alerts` and subscribe your email.
- Provision `aws_budgets_budget` of type `COST`, monthly limit `$100`.
- Add four `notification` blocks at 10%, 25%, 50%, 75% of actual spend, all to the SNS topic.
- Confirm the SNS email subscription (click the link AWS sends).
- Verify by triggering a tiny chargeable action and waiting for the first alert.

---

### Issue 2: Provision VPC with configurable AZs and subnet topology

**Required:** A reusable VPC Terraform module supporting 1 to 3 AZs and optional private subnets. Dev passes `availability_zones = ["us-east-1a"]` and `enable_private_subnets = false`. Prod passes two AZs with private subnets enabled, without module changes.

**How:**
- Create `terraform/modules/vpc/` with `main.tf`, `variables.tf`, `outputs.tf`.
- Inputs: `cidr_block` (default `10.0.0.0/16`), `availability_zones` (list), `enable_private_subnets` (bool), `enable_nat` (bool).
- Use `count` or `for_each` on subnet resources so private subnets only exist when the flag is true.
- Outputs: `vpc_id`, `public_subnet_ids`, `private_subnet_ids`.

---

### Issue 3: Configure Internet Gateway and conditional NAT Gateway

**Required:** Internet Gateway always provisioned (free). NAT Gateway gated behind `enable_nat`. Dev keeps NAT off to save $32/mo. The NAT code path must exist and be testable in prod tfvars.

**How:**
- Inside the VPC module, always create `aws_internet_gateway`.
- Create `aws_eip` and `aws_nat_gateway` with `count = var.enable_nat ? 1 : 0`.
- When NAT is enabled, place it in the first public subnet.
- When NAT is disabled, private subnets (if any) have no egress — intentional for dev.

---

### Issue 4: Create route tables for public and private subnets

**Required:** A public route table routing `0.0.0.0/0` to the IGW, associated with all public subnets. A private route table that routes to the NAT Gateway when enabled, otherwise has no default route.

**How:**
- Create `aws_route_table` for public; add `aws_route` for `0.0.0.0/0` to IGW.
- Loop `aws_route_table_association` over all public subnet IDs.
- Create `aws_route_table` for private (only when private subnets exist).
- Add the NAT default route conditionally with `count = var.enable_nat ? 1 : 0`.

---

### Issue 5: Define security groups for EKS nodes and ALB

**Required:** Two security groups: one for EKS worker nodes (inter-node and pod traffic), one for the ALB (inbound 443 from internet). Both built in dev, but ALB SG remains unattached until `make demo` provisions an ALB.

**How:**
- Create `terraform/modules/vpc/security_groups.tf`.
- Node SG: ingress from self (all ports), from ALB SG on 1025-65535. Egress all.
- ALB SG: ingress on 443 from `0.0.0.0/0` and on 80 (redirect). Egress to node SG only.
- Output both SG IDs for EKS and ALB modules to reference.

---

### Issue 6: Package VPC as a clean Terraform module

**Required:** The VPC code from issues 2-5 packaged as a self-contained module consumable from `terraform/environments/dev/main.tf` with a single `module "vpc"` block.

**How:**
- Move all VPC resources into `terraform/modules/vpc/`.
- Declare inputs in `variables.tf` with descriptions, types, sane defaults.
- Declare outputs: `vpc_id`, `public_subnet_ids`, `private_subnet_ids`, `node_security_group_id`, `alb_security_group_id`.
- In `terraform/environments/dev/main.tf`, consume with `source = "../../modules/vpc"`.

---

### Issue 7: Validate full destroy and re-apply cycle works cleanly

**Required:** Proof that `terraform destroy` followed by `terraform apply` produces identical infrastructure with zero leftover resources and zero errors. This is the foundation of cost discipline.

**How:**
- Run `terraform apply` from a clean state.
- Note all resource IDs in AWS Console.
- Run `terraform destroy`. Verify no orphan ENIs, EIPs, or subnets remain.
- Run `terraform apply` again. Confirm `terraform plan` after apply shows "No changes."
- Document any manual cleanup in `docs/runbooks/teardown-checklist.md`.

---

### Issue 7a: Write Makefile with up / down / nuke / cost targets

**Required:** A single `Makefile` at the repo root abstracting the cost lifecycle into one-word commands. Typing `make down` at the end of every session must become a reflex.

**How:**
- Create `Makefile` with targets:
  - `bootstrap`: runs `terraform init && apply` in `terraform/bootstrap/`.
  - `up`: `terraform apply -auto-approve` in `terraform/environments/dev/` then `helm install`.
  - `down`: `helm uninstall` then `terraform destroy -auto-approve`.
  - `nuke`: destroys the bootstrap stack after confirmation prompt.
  - `cost`: `aws ce get-cost-and-usage` for current month.
- Add `.PHONY` declarations and a `help` target.

---

## Milestone 2 — Container Platform

**Due:** Week 4
**Theme:** Add the runtime — EKS cluster, ECR registry, FastAPI app, Helm chart. Cluster runs in the dev VPC's public subnet on one spot node. End state: deploy the app, hit `/health` via `kubectl port-forward`, tear down for under $1.

---

### Issue 8: Write Terraform module for EKS cluster

**Required:** A reusable EKS module supporting public OR private node placement via variable. Dev uses public (no NAT cost). Prod uses private. Module also provisions the OIDC provider for IRSA.

**How:**
- Create `terraform/modules/eks/`.
- Inputs: `cluster_name`, `cluster_version` (default `1.30`), `subnet_ids`, `node_subnet_placement`, `node_security_group_id`.
- Use `aws_eks_cluster` and `aws_iam_role` for the cluster service role.
- Provision `aws_iam_openid_connect_provider` from the cluster's OIDC issuer URL.
- Outputs: `cluster_endpoint`, `cluster_name`, `oidc_provider_arn`, `oidc_provider_url`.

---

### Issue 9: Configure managed node group with t3.small SPOT for dev

**Required:** A managed node group: dev runs 1x t3.small SPOT (~$0.007/hr). Prod variable: 2x t3.medium on-demand.

**How:**
- Add `aws_eks_node_group` inside the EKS module.
- Inputs: `instance_types` (default `["t3.small"]`), `capacity_type` (`"SPOT"`), `desired_size` (1), `min_size` (1), `max_size` (2).
- Attach IAM policies: `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, `AmazonEC2ContainerRegistryReadOnly`.
- Verify: `aws eks update-kubeconfig --region us-east-1 --name verdict-dev` then `kubectl get nodes` shows `Ready`.

---

### Issue 10: Create ECR repository with scan-on-push and image lifecycle

**Required:** A private ECR repository with scan-on-push enabled and a lifecycle policy keeping only the last 5 images, preventing old SHA builds from accumulating cost.

**How:**
- Create `terraform/modules/ecr/`.
- `aws_ecr_repository` with `image_scanning_configuration { scan_on_push = true }` and `image_tag_mutability = "IMMUTABLE"`.
- `aws_ecr_lifecycle_policy` with rule "Keep last 5 images" (`countType = "imageCountMoreThan"`, `countNumber = 5`).
- Output `repository_url`.

---

### Issue 11: Configure IRSA service account for application pods

**Required:** A Kubernetes ServiceAccount annotated with an IAM role ARN so pods receive short-lived AWS credentials scoped to Secrets Manager reads and ECR pulls. No long-lived credentials in the pod.

**How:**
- Create `terraform/modules/iam/irsa.tf`.
- IAM role `verdict-app-irsa` with trust policy referencing the OIDC provider and restricting `sub` to `system:serviceaccount:verdict:verdict-app`.
- Policy grants `secretsmanager:GetSecretValue` on the secret ARN and `ecr:GetAuthorizationToken` / `ecr:BatchGetImage`.
- In `helm/verdict-app/templates/serviceaccount.yaml`, annotate with `eks.amazonaws.com/role-arn`.

---

### Issue 12: Install AWS Load Balancer Controller via Helm (no Ingress by default)

**Required:** The AWS Load Balancer Controller deployed so any future Ingress can provision an ALB. In dev, no Ingress is created by default — only when `make demo` runs. Footprint stays near zero.

**How:**
- Add `helm_release` resource pointing to the `eks/aws-load-balancer-controller` chart.
- Configure with `set { name = "clusterName", value = var.cluster_name }`.
- Create the controller's IRSA role with scoped ELB permissions.
- Make Ingress conditional on `.Values.ingress.enabled` (false in dev values, true in prod).

---

### Issue 13: Build FastAPI application with /run-test, /health, /results endpoints

**Required:** A minimal FastAPI service simulating a test runner.
- `POST /run-test`: accepts a test file, returns pass/fail.
- `GET /health`: returns 200 for liveness.
- `GET /results`: returns all results so far.

**How:**
- Create `app/main.py` with FastAPI app and three routes.
- `POST /run-test`: accept `{"test_file": "..."}`, run `pytest <file>` via `subprocess.run`, return `{"status": "pass|fail", "stdout": "...", "duration_ms": N}`.
- `GET /health`: return `{"status": "ok"}`.
- `GET /results`: return list from a module-level dict.
- `app/requirements.txt`: `fastapi`, `uvicorn`, `pytest`.
- Local run: `uvicorn app.main:app --reload`. Verify with `curl`.

---

### Issue 14: Write multi-stage Dockerfile with non-root user

**Required:** A Dockerfile producing a small, hardened image. Multi-stage to keep build tools out of runtime. Non-root user (UID 10001). Final image under 200 MB.

**How:**
- Stage 1 `builder`: `FROM python:3.12-slim`, install build deps, `pip install --target=/install -r requirements.txt`.
- Stage 2 `runtime`: `FROM python:3.12-slim`, `COPY --from=builder /install ...`, `COPY app/ /app/`.
- `RUN useradd -u 10001 -m appuser && chown -R appuser /app`.
- `USER 10001`, `WORKDIR /app`, `EXPOSE 8080`, `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]`.
- Build: `docker build -t verdict-app:dev app/`. Verify `docker run --rm -p 8080:8080 verdict-app:dev` serves `/health`.

---

### Issue 15: Write Helm chart with dev and prod values files

**Required:** A single Helm chart `verdict-app` with two values files.
- `values-dev.yaml`: 1 replica, no Ingress, no HPA, minimal requests.
- `values-prod.yaml`: 2 replicas, Ingress enabled, HPA on CPU.

**How:**
- Create `helm/verdict-app/` with `Chart.yaml`, both values files, `templates/`.
- Templates: `deployment.yaml`, `service.yaml` (ClusterIP), `ingress.yaml` (conditional), `serviceaccount.yaml`, `hpa.yaml` (conditional).
- In `deployment.yaml`: image from values, livenessProbe on `/health`, securityContext per Issue 30.
- Verify: `helm template verdict-app ./helm/verdict-app -f values-dev.yaml` — confirm no Ingress rendered.

---

### Issue 16: Deploy application to EKS and verify access via port-forward

**Required:** App running on the cluster, reachable from your laptop via `kubectl port-forward` — no ALB provisioned. ALB verification is a gated sub-task behind `make demo`.

**How:**
- Build and push: `docker build -t <ecr_url>:dev app/ && docker push ...`.
- `helm install verdict-app ./helm/verdict-app -n verdict --create-namespace -f values-dev.yaml --set image.tag=dev`.
- `kubectl port-forward -n verdict svc/verdict-app 8080:80`.
- `curl localhost:8080/health` returns `{"status":"ok"}`.
- Demo path: switch to `values-prod.yaml`, confirm ALB provisions, hit DNS, tear down.

---

## Milestone 3 — CI/CD Pipeline

**Due:** Week 6
**Theme:** Wire GitHub Actions to AWS via OIDC. PRs build, deploy to EKS, run tests, comment results, gate merge on failure. End state: open a PR, see green or red in under 3 minutes.

---

### Issue 17: Configure GitHub OIDC provider in AWS IAM (in Milestone 1 bootstrap)

**Required:** An IAM OIDC identity provider for `token.actions.githubusercontent.com` so GitHub Actions can exchange its JWT for short-lived AWS credentials. One-time, account-wide. Lives in `terraform/bootstrap/` so it survives `make down`.

**How:**
- Add `aws_iam_openid_connect_provider` in `terraform/bootstrap/main.tf`.
- `url = "https://token.actions.githubusercontent.com"`, `client_id_list = ["sts.amazonaws.com"]`.
- Use the current GitHub OIDC thumbprint from AWS docs.

---

### Issue 18: Create IAM role for GitHub Actions with scoped trust policy

**Required:** An IAM role `gha-verdict-deploy` that GitHub Actions assumes via OIDC. Trust policy restricts assumption to your specific repository — never any repository, never any branch.

**How:**
- In `terraform/bootstrap/`, create `aws_iam_role` with `assume_role_policy` referencing the OIDC provider ARN.
- Condition: `StringEquals` on `aud = "sts.amazonaws.com"` and `StringLike` on `sub = "repo:abhishek-singh/verdict:*"`.
- Permissions: ECR push, EKS describe, Helm-needed K8s API access via `aws-auth` ConfigMap.
- Output the role ARN.

---

### Issue 19: Write detect_changed_tests.py using git diff

**Required:** A Python script comparing the PR branch against the base branch, returning the list of changed files matching `app/tests/test_*.py`. Empty list means the gate exits early and allows merge.

**How:**
- Create `.github/scripts/detect_changed_tests.py`.
- `subprocess.run(["git", "diff", "--name-only", f"{base_sha}...{head_sha}"], capture_output=True)`.
- Filter with `fnmatch.filter(lines, "app/tests/test_*.py")`.
- Emit as GitHub Actions output via `$GITHUB_OUTPUT`.
- Test locally: `python detect_changed_tests.py --base main --head HEAD`.

---

### Issue 20: Write pr-test-gate.yml workflow with OIDC authentication

**Required:** A GitHub Actions workflow triggered on `pull_request`, configured with `permissions: id-token: write` so it can request an OIDC token and assume the IAM role from Issue 18. No static AWS keys in repo secrets.

**How:**
- Create `.github/workflows/pr-test-gate.yml`.
- `on: pull_request: branches: [main]`.
- Top-level `permissions: id-token: write, contents: read, pull-requests: write`.
- Step: `uses: aws-actions/configure-aws-credentials@v4` with `role-to-assume: <arn>`, `aws-region: us-east-1`.

---

### Issue 21: Implement test execution against FastAPI app in workflow

**Required:** Workflow steps that build the image, push to ECR, ensure the cluster is up, helm-upgrade the test runner, POST each changed test file to `/run-test`, and aggregate results.

**How:**
- Step: `docker build -t $ECR_URL:${{ github.sha }} app/ && docker push ...`.
- Step: `aws eks update-kubeconfig --name verdict-dev`.
- Step: `helm upgrade --install verdict-app ./helm/verdict-app -f values-dev.yaml --set image.tag=${{ github.sha }} --wait`.
- Step: run `.github/scripts/run_tests.py` which port-forwards, posts each file, aggregates results into JSON.

---

### Issue 22: Add PR comment step with pass/fail results

**Required:** A workflow step that posts a sticky comment on the PR summarizing results — count passed, count failed, names of failing tests, link to the workflow run.

**How:**
- Create `.github/scripts/post_pr_comment.py`.
- Use the GitHub REST API via `${{ secrets.GITHUB_TOKEN }}`.
- Add a marker line at the top (e.g. `<!-- verdict-test-gate -->`) and upsert: edit if exists, else create.
- Format the body as a markdown table.

---

### Issue 23: Configure branch protection to require pr-test-gate status check

**Required:** Branch protection rule on `main` blocking merge unless `pr-test-gate` succeeds. This is what makes the project a real gate, not a notification.

**How:**
- In GitHub, Settings, Branches, add rule for `main`.
- Enable "Require status checks to pass before merging".
- Add `pr-test-gate` as required (appears after the workflow runs once).
- Enable "Require branches to be up to date".
- Enable "Do not allow bypassing the above settings".

---

### Issue 24: Write deploy-infrastructure.yml for Terraform plan on PR and apply on merge

**Required:** A second workflow that runs `terraform plan` on every PR touching `terraform/**` and posts the plan as a PR comment. On merge to `main`, runs `terraform apply`.

**How:**
- Create `.github/workflows/deploy-infrastructure.yml`.
- Trigger: `on: pull_request: paths: ["terraform/**"]` and `on: push: branches: [main]: paths: ["terraform/**"]`.
- PR job: `terraform init`, `terraform plan -out=tfplan`, post plan as PR comment.
- Merge job: `terraform init`, `terraform apply -auto-approve`.
- Uses the OIDC role from Issue 18.

---

### Issue 25: Test full PR gating flow end to end

**Required:** Proof the chain works. Passing test PR turns gate green and allows merge. Failing test PR turns gate red, blocks merge, comment shows failure.

**How:**
- Branch `test/passing-gate`: add `app/tests/test_dummy_pass.py` with `def test_ok(): assert True`. Push, open PR.
- Verify: workflow runs, comment posted, status green, merge enabled.
- Branch `test/failing-gate`: add `def test_fail(): assert False`. Push, open PR.
- Verify: workflow runs, comment shows fail, status red, merge disabled.
- Close both PRs. Document with screenshots in `docs/runbooks/pr-gate-demo.md`.

---

### Issue 25a: Write nightly-teardown.yml schedule workflow as cost insurance

**Required:** A scheduled workflow running every night at 23:00 IST that destroys EKS and node group if still up. Safety net for forgotten `make down`.

**How:**
- Create `.github/workflows/nightly-teardown.yml`.
- Trigger: `on: schedule: - cron: "30 17 * * *"` (17:30 UTC = 23:00 IST).
- Step: assume OIDC role, check `aws eks describe-cluster --name verdict-dev`, if found run `terraform destroy -target=module.eks -auto-approve`.
- Do NOT destroy VPC or bootstrap — only expensive compute.
- Add `workflow_dispatch` for manual runs.

---

## Milestone 4 — Observability and Security

**Due:** Week 8
**Theme:** Add the operational and security layers. Structured logs, golden-signal dashboards, secrets in Secrets Manager, hardened pod security context. End state: interview-ready — dashboard, security walkthrough, proven budget compliance.

---

### Issue 26: Enable CloudWatch Container Insights with 1-day log retention in dev

**Required:** CloudWatch Container Insights on EKS collecting node and pod metrics. Log retention 1 day in dev, 7 days in prod to control ingestion cost.

**How:**
- Install `amazon-cloudwatch-observability` EKS Add-On via `aws_eks_addon`.
- Create `aws_cloudwatch_log_group` for `/aws/containerinsights/verdict-dev/application`, `dataplane`, `host` with `retention_in_days = 1` (parameterized).
- Verify in CloudWatch Console: Container Insights, Performance monitoring, see CPU/memory by pod.

---

### Issue 27: Implement structured JSON logging in FastAPI

**Required:** All app logs as single-line JSON with timestamp, level, service, request_id, custom fields. Makes Logs Insights queries trivial.

**How:**
- In `app/main.py`, configure Python `logging` with a JSON formatter (`python-json-logger`).
- FastAPI middleware injects `request_id` (UUID4) per request via `contextvars`.
- Log every request: `logger.info("request_completed", extra={"path": ..., "status": ..., "duration_ms": ...})`.
- Verify: `fields @timestamp, level, path, duration_ms | sort @timestamp desc | limit 20` in Logs Insights.

---

### Issue 28: Create CloudWatch dashboard with golden signals

**Required:** A CloudWatch dashboard managed in Terraform showing the four golden signals (latency, traffic, errors, saturation) plus pod CPU/memory. Dashboard-as-code, no manual clicking.

**How:**
- Create `terraform/modules/observability/dashboard.tf`.
- `aws_cloudwatch_dashboard` with 6 widgets:
  1. Latency: `duration_ms` p50/p95/p99 (metric filter from JSON logs)
  2. Traffic: requests per minute
  3. Errors: 5xx rate
  4. Saturation: pod CPU and memory
  5. Pipeline duration: PR open to gate result
  6. EKS node count
- Verify rendering in CloudWatch Console.

---

### Issue 29: Migrate application secrets to AWS Secrets Manager

**Required:** No secrets in env vars, ConfigMaps, images, or Terraform state. App reads at runtime via IRSA-scoped IAM permission.

**How:**
- Create one secret (e.g. `verdict/app/api-key`) encrypted with a customer-managed KMS key.
- In `app/main.py`, on startup call `boto3.client("secretsmanager").get_secret_value(SecretId=...)`.
- IRSA role (Issue 11) must include `secretsmanager:GetSecretValue` on the secret ARN and `kms:Decrypt` on the CMK.
- Verify: `kubectl exec` into the pod, run `env`, confirm no key visible.

---

### Issue 30: Add container security context to Helm chart

**Required:** Deployment must run non-root, read-only root FS, no privilege escalation, all Linux capabilities dropped. Pod-level defense-in-depth.

**How:**
- In `helm/verdict-app/templates/deployment.yaml`, under `spec.template.spec`:
  - Pod: `securityContext.runAsNonRoot: true`, `runAsUser: 10001`, `fsGroup: 10001`.
  - Container: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault`.
- Add `emptyDir` volume mounted at `/tmp` so uvicorn can write.
- Verify: `kubectl describe pod`, then `kubectl exec ... -- touch /test` — should fail.

---

### Issue 31: Write README with architecture diagram and setup instructions

**Required:** A repo-level README that lets a recruiter understand the project in under 2 minutes and run it locally in under 15.

**How:**
- Sections: elevator pitch, architecture diagram (Mermaid), tech stack table, quick start (`make bootstrap`, `make up`, `make demo`, `make down`), cost story (with Cost Explorer screenshot), security highlights, link to `architecture.md`.
- Include a screenshot or GIF of a passing PR and a failing PR.
- Pin the repo on your GitHub profile.

---

### Issue 32: Final cost review and cleanup

**Required:** Documented audit at end of week 8 confirming spend is well under the $100 budget, with screenshots and a closing decision: keep bootstrap running for demos, or `make nuke` to archive.

**How:**
- Run `make cost`, screenshot.
- Open Cost Explorer, filter by tag `Project=verdict`, screenshot the 8-week trend.
- Update README with final spend (target: under $20).
- Audit IAM, ECR, CloudWatch for orphans; clean up.
- Decide: keep bootstrap (~$1/mo) for demos OR `make nuke` and archive.

---

## Net Changes vs. Original Issue List

| Change | Count | Issues |
|---|---|---|
| Reworded for cost mode | 6 | 2, 3, 8, 9, 12, 16, 26 |
| Added | 3 | 1a (Budget), 7a (Makefile), 25a (Nightly teardown) |
| Removed | 0 | — |
| Moved earlier | 1 | 17 (OIDC) → Milestone 1 bootstrap |
| Split | 1 | 15 (Helm chart) → chart + two values files |

Milestone themes, ordering, and 2-week cadence are unchanged. The 8-week timeline is realistic alongside SAA prep and a day job.
