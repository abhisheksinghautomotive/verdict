resource "aws_cloudwatch_log_group" "containerinsights_application" {
  name              = "/aws/containerinsights/${module.eks.cluster_name}/application"
  retention_in_days = var.container_insights_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "/aws/containerinsights/${module.eks.cluster_name}/application"
    }
  )
}

resource "aws_cloudwatch_log_group" "containerinsights_dataplane" {
  name              = "/aws/containerinsights/${module.eks.cluster_name}/dataplane"
  retention_in_days = var.container_insights_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "/aws/containerinsights/${module.eks.cluster_name}/dataplane"
    }
  )
}

resource "aws_cloudwatch_log_group" "containerinsights_host" {
  name              = "/aws/containerinsights/${module.eks.cluster_name}/host"
  retention_in_days = var.container_insights_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "/aws/containerinsights/${module.eks.cluster_name}/host"
    }
  )
}

resource "aws_cloudwatch_log_group" "containerinsights_performance" {
  name              = "/aws/containerinsights/${module.eks.cluster_name}/performance"
  retention_in_days = var.container_insights_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "/aws/containerinsights/${module.eks.cluster_name}/performance"
    }
  )
}

resource "aws_eks_addon" "cloudwatch_observability" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "amazon-cloudwatch-observability"
  addon_version            = "v6.2.0-eksbuild.1"
  service_account_role_arn = module.iam.cloudwatch_observability_role_arn

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    module.eks.node_group_arn,
    aws_cloudwatch_log_group.containerinsights_application,
    aws_cloudwatch_log_group.containerinsights_dataplane,
    aws_cloudwatch_log_group.containerinsights_host,
    aws_cloudwatch_log_group.containerinsights_performance
  ]

  tags = local.common_tags
}

