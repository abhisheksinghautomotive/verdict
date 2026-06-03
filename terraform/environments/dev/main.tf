locals {
  common_tags = {
    Project     = "verdict"
    Environment = "dev"
    ManagedBy   = "terraform"
    CostCenter  = "personal"
  }
}

module "vpc" {
  source = "../../modules/vpc"

  cidr_block             = "10.0.0.0/16"
  availability_zones     = ["ap-south-1a", "ap-south-1b"]
  enable_private_subnets = false
  enable_nat             = false
  common_tags            = local.common_tags
}

module "eks" {
  source = "../../modules/eks"

  cluster_name           = "verdict-dev"
  cluster_version        = "1.30"
  subnet_ids             = module.vpc.public_subnet_ids
  node_subnet_placement  = [module.vpc.public_subnet_ids[0]]
  node_security_group_id = module.vpc.node_security_group_id
  common_tags            = local.common_tags
}

module "ecr" {
  source = "../../modules/ecr"

  repository_name = "verdict-dev"
  common_tags     = local.common_tags
}

module "iam" {
  source = "../../modules/iam"

  oidc_provider_arn  = module.eks.oidc_provider_arn
  oidc_provider_url  = module.eks.oidc_provider_url
  ecr_repository_arn = module.ecr.repository_arn
  common_tags        = local.common_tags
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.8.1"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.iam.alb_controller_role_arn
  }

  set {
    name  = "vpcId"
    value = module.vpc.vpc_id
  }

  set {
    name  = "region"
    value = var.aws_region
  }

  depends_on = [
    module.eks.node_group_arn
  ]
}




