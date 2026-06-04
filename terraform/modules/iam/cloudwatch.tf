# IAM policy document for assuming role via OIDC for CloudWatch Observability addon
data "aws_iam_policy_document" "cloudwatch_observability_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:amazon-cloudwatch:cloudwatch-agent"]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }

    principals {
      identifiers = [var.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

# IAM Role for CloudWatch Observability addon pods
resource "aws_iam_role" "cloudwatch_observability" {
  name               = "verdict-cloudwatch-observability-irsa"
  assume_role_policy = data.aws_iam_policy_document.cloudwatch_observability_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-cloudwatch-observability-irsa"
    }
  )
}

# Attach standard CloudWatch agent policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_server_policy" {
  role       = aws_iam_role.cloudwatch_observability.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}
