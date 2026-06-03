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
  availability_zones     = ["ap-south-1a"]
  enable_private_subnets = false
  enable_nat             = false
  common_tags            = local.common_tags
}
