resource "aws_security_group" "eks_nodes" {
  name        = "verdict-eks-nodes-sg"
  description = "Security group for EKS worker nodes"
  vpc_id      = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-eks-nodes-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "eks_nodes_self" {
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow all ingress from self"

  referenced_security_group_id = aws_security_group.eks_nodes.id
  ip_protocol                  = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "eks_nodes_from_alb" {
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow inbound traffic from ALB security group"

  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 1025
  to_port                      = 65535
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "eks_nodes_egress_all" {
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow all outbound traffic"

  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "-1"
}

resource "aws_security_group" "alb" {
  name        = "verdict-alb-sg"
  description = "Security group for application load balancer"
  vpc_id      = aws_vpc.this.id

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-alb-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTPS from internet"

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTP from internet for redirect"

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_eks_nodes" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow outbound traffic to EKS nodes only"

  referenced_security_group_id = aws_security_group.eks_nodes.id
  from_port                    = 1025
  to_port                      = 65535
  ip_protocol                  = "tcp"
}
