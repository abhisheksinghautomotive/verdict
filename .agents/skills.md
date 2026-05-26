# Verdict Skill Map

This document establishes the curated, token-efficient subset of Antigravity skills mapped directly to Verdict's 8-week implementation timeline. Only these skills should be loaded or referenced during agent execution to minimize token overhead.

---

## 1. Skill Matrix

| Milestone | Target Domain | Required Skill | Primary Purpose |
|---|---|---|---|
| **M1: Foundation** | IaC, VPC, Cost Budgets | `terraform-skill`<br/>`terraform-module-library`<br/>`aws-skills`<br/>`cost-optimization` | Standardize modular Terraform layout, tag conventions, single-AZ spot limitations, and budget alerts. |
| **M2: Container** | Docker, EKS, FastAPI, Helm | `docker-expert`<br/>`helm-chart-scaffolding`<br/>`python-pro` | Construct minimal (<200MB) non-root multi-stage images, standard Helm templates with dev/prod values, and robust FastAPI routes. |
| **M3: CI/CD** | GitHub Actions, Git Workflows | `github`<br/>`github-actions-templates` | Configure secure GitHub-to-AWS OIDC federation, branch protection policies, and automated PR-gating test execution runners. |
| **M4: Ops & Sec** | Observability, Secrets, Security | `secrets-management`<br/>`observability-monitoring-monitor-setup` | Implement KMS customer-managed encryption, pod hardening security context (UID 10001, read-only FS), and custom CloudWatch dashboards. |
| **All Phase** | System Diagnostics | `systematic-debugging`<br/>`writing-plans`<br/>`executing-plans` | Enforce systematic root-cause analysis for pipeline/test failures and plan tracking. |

---

## 2. Milestone Execution Guidance

### Milestone 1 — Foundation Infrastructure (Weeks 1-2)
* **`terraform-skill` / `terraform-module-library`**: Used to structure the remote S3 state, configure state locking via DynamoDB, build the public/private VPC subnets conditionally (`for_each`), and establish resources tags: `Project=verdict`, `Environment=dev`, `ManagedBy=terraform`, `CostCenter=personal`.
* **`cost-optimization`**: Guides the configuration of the conditional NAT Gateway logic, keeping it disabled in development (saving $32/mo) and generating AWS Budget alerts at $10 / $25 / $50 / $75 thresholds.

### Milestone 2 — Container Platform (Weeks 3-4)
* **`docker-expert`**: Directs the multi-stage FastAPI build using `python:3.12-slim` as the base, running under a non-root UID 10001, and ensuring the final runtime image is stripped of build-time dependencies to keep the size under 200MB.
* **`helm-chart-scaffolding`**: Used to scaffold the `verdict-app` chart, configuring liveness/readiness probes, defining custom service accounts annotated with IRSA role ARNs, and separating environment values (`values-dev.yaml` and `values-prod.yaml`).
* **`python-pro`**: Sets up the FastAPI router, implements the `/run-test`, `/health`, and `/results` endpoints, and structures the `pytest` runner subsystem executing under `subprocess.run()`.

### Milestone 3 — CI/CD Pipeline (Weeks 5-6)
* **`github-actions-templates`**: Used to build `.github/workflows/pr-test-gate.yml` and `deploy-infrastructure.yml` using modern GitHub workflows, secure `id-token: write` permissions, and action hashing for security.
* **`github`**: Used to write automated scripts that interface with the GitHub REST API to post-gate verdicts as PR comments and manage PR state updates.

### Milestone 4 — Observability and Security (Weeks 7-8)
* **`observability-monitoring-monitor-setup`**: Handles CloudWatch Container Insights configuration, structured JSON logging formatter, custom CloudWatch metrics queries, and the Terraform-configured golden-signals dashboard.
* **`secrets-management`**: Secures application APIs, database creds, and tokens using AWS Secrets Manager encrypted with customer-managed KMS keys, eliminating environment-level plaintext secrets.

---

## 3. General Troubleshooting Workflow

When any task fails compilation, validation, linting, or integration checks, enforce the `systematic-debugging` loop:
1. Capture precise exit codes and error output from standard execution.
2. Verify system state (e.g., local configuration, EKS node capacity, IAM permissions).
3. Validate locally (e.g., `make test-gate`, `helm lint`, `terraform validate`, `ruff check`).
4. Remediate structural cause first; never implement quick-fix overrides.
