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

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-igw"
    }
  )
}

resource "aws_eip" "nat" {
  count = var.enable_nat ? 1 : 0

  domain = "vpc"

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-nat-eip"
    }
  )
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[var.availability_zones[0]].id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-nat"
    }
  )

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-public-rt"
    }
  )
}

resource "aws_route" "public_internet_access" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count  = var.enable_private_subnets ? 1 : 0
  vpc_id = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-private-rt"
    }
  )
}

resource "aws_route" "private_nat_gateway" {
  count                  = var.enable_private_subnets && var.enable_nat ? 1 : 0
  route_table_id         = aws_route_table.private[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[0].id
}

resource "aws_route_table_association" "private" {
  for_each = local.private_subnets

  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private[0].id
}



