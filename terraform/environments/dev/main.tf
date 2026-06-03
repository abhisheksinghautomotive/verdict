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


