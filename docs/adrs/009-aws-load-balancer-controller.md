# 009. AWS Load Balancer Controller Installation
Date: 2026-06-03
Status: Accepted

Context:
The Verdict platform runs on Amazon EKS and needs to expose the application to external traffic for demos and validation. An Application Load Balancer (ALB) is required to route HTTP/HTTPS traffic from the public internet to pods inside the cluster. To provision and manage ALBs dynamically using Kubernetes Ingress resources, we need to install the AWS Load Balancer Controller.

Decision:
We will:
1. Provision a dedicated IAM role (`aws-load-balancer-controller-irsa`) using IAM Roles for Service Accounts (IRSA) that trusts the EKS OIDC provider and authorizes the `aws-load-balancer-controller` service account in the `kube-system` namespace.
2. Attach a scoped IAM policy (`aws-load-balancer-controller-policy`) containing standard ELB, ACM, Cognito, and WAF permissions required by the controller.
3. Deploy the `aws-load-balancer-controller` Helm release in the `kube-system` namespace using the `helm_release` Terraform resource, mapping it to the EKS cluster and the IRSA role.
4. Add support for conditional Ingress resource creation in the `verdict-app` Helm chart, controlled by the `.Values.ingress.enabled` boolean flag (disabled in dev, enabled in prod).

Consequences:
- The AWS Load Balancer Controller will run as a deployment in the EKS cluster.
- When an Ingress resource is created with class `alb`, the controller will automatically spin up an AWS Application Load Balancer, register targets, and configure listeners.
- Dev footprint remains near zero because Ingress is disabled by default in `values-dev.yaml`.

Cost impact:
- $0/hr active and $0/mo at rest in Dev mode because the controller itself runs on the existing EKS worker nodes and no ALB is provisioned by default.
- Prod mode will incur standard ALB pricing ($0.0225/hr + LCU charges) only when Ingress is enabled.
