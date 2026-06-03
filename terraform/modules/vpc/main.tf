locals {
  public_subnets = {
    for idx, az in var.availability_zones : az => {
      cidr_block = cidrsubnet(var.cidr_block, 8, idx)
    }
  }

  private_subnets = var.enable_private_subnets ? {
    for idx, az in var.availability_zones : az => {
      cidr_block = cidrsubnet(var.cidr_block, 8, idx + 10)
    }
  } : {}
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-vpc"
    }
  )
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.key

  map_public_ip_on_launch = true

  tags = merge(
    var.common_tags,
    {
      Name                     = "verdict-public-${each.key}"
      "kubernetes.io/role/elb" = "1"
    }
  )
}

resource "aws_subnet" "private" {
  for_each = local.private_subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.key

  tags = merge(
    var.common_tags,
    {
      Name                              = "verdict-private-${each.key}"
      "kubernetes.io/role/internal-elb" = "1"
    }
  )
}
