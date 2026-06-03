.DEFAULT_GOAL := help

# Configuration variables
ALERT_EMAIL ?=

.PHONY: help bootstrap up down nuke cost

help:
	@echo "Verdict Platform Lifecycle Manager"
	@echo "Usage: make [target] [ALERT_EMAIL=user@example.com]"
	@echo ""
	@echo "Targets:"
	@echo "  bootstrap   Initialize and apply the Terraform bootstrap stack"
	@echo "              Usage: make bootstrap [ALERT_EMAIL=user@example.com]"
	@echo "  up          Provision dev infrastructure and deploy Helm application"
	@echo "  down        Tear down the Helm application and dev infrastructure"
	@echo "  nuke        Destroy the Terraform bootstrap stack (requires confirmation)"
	@echo "  cost        Fetch current month AWS costs via Cost Explorer"
	@echo "  help        Display this help message"

bootstrap:
	cd terraform/bootstrap && terraform init
	@if [ -n "$(ALERT_EMAIL)" ]; then \
		cd terraform/bootstrap && terraform apply -var="alert_email=$(ALERT_EMAIL)"; \
	else \
		cd terraform/bootstrap && terraform apply; \
	fi

up:
	cd terraform/environments/dev && terraform init -backend-config=backend.tfvars && terraform apply -auto-approve
	@if [ -d "helm/verdict-app" ]; then \
		echo "Installing Helm chart..."; \
		aws eks update-kubeconfig --region ap-south-1 --name verdict-dev; \
		helm upgrade --install verdict-app ./helm/verdict-app -n verdict --create-namespace -f helm/verdict-app/values-dev.yaml; \
	else \
		echo "Helm chart directory not found. Skipping Helm installation."; \
	fi

down:
	@if which helm >/dev/null 2>&1 && helm list -n verdict 2>/dev/null | grep -q verdict-app; then \
		echo "Uninstalling Helm release..."; \
		helm uninstall verdict-app -n verdict || true; \
	fi
	cd terraform/environments/dev && terraform destroy -auto-approve

nuke:
	@printf "WARNING: This will destroy the bootstrap stack (tfstate S3 bucket, DynamoDB lock table, and budget).\nAre you sure you want to proceed? [y/N]: " && read ans && [ "$${ans}" = "y" -o "$${ans}" = "Y" ] || { echo "Nuke aborted."; exit 1; }
	cd terraform/bootstrap && terraform destroy -var="alert_email=dummy@example.com" -auto-approve

cost:
	@START_DATE=$$(python3 -c "import datetime; print(datetime.date.today().strftime('%Y-%m-01'))") && \
	END_DATE=$$(python3 -c "import datetime; print((datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'))") && \
	echo "Querying AWS Cost Explorer from $${START_DATE} to $${END_DATE}..." && \
	aws ce get-cost-and-usage \
		--time-period Start=$${START_DATE},End=$${END_DATE} \
		--granularity MONTHLY \
		--metrics "UnblendedCost"
