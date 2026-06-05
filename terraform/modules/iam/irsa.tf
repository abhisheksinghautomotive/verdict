data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  secrets_manager_arn = var.secrets_manager_secret_arn != null ? var.secrets_manager_secret_arn : "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:verdict/*"
}

# IAM policy document for assuming role via OIDC
data "aws_iam_policy_document" "irsa_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:verdict:verdict-app"]
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

# IAM Role for Verdict application pods
resource "aws_iam_role" "verdict_app" {
  name               = "verdict-app-irsa"
  assume_role_policy = data.aws_iam_policy_document.irsa_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-app-irsa"
    }
  )
}

# IAM Policy for Verdict application pods (Secrets Manager and ECR)
data "aws_iam_policy_document" "verdict_app" {
  statement {
    sid       = "SecretsManagerGet"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [local.secrets_manager_arn]
  }

  dynamic "statement" {
    for_each = var.kms_key_arn != null ? [var.kms_key_arn] : []
    content {
      sid       = "KMSDecrypt"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = [statement.value]
    }
  }

  statement {
    sid       = "ECRGetAuthToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] # GetAuthorizationToken is registry-level, requires "*"
  }

  statement {
    sid       = "ECRBatchGetImage"
    effect    = "Allow"
    actions   = ["ecr:BatchGetImage"]
    resources = [var.ecr_repository_arn]
  }
}

resource "aws_iam_policy" "verdict_app" {
  name        = "verdict-app-policy"
  description = "Policy for verdict-app pods to access Secrets Manager and ECR"
  policy      = data.aws_iam_policy_document.verdict_app.json

  tags = merge(
    var.common_tags,
    {
      Name = "verdict-app-policy"
    }
  )
}

resource "aws_iam_role_policy_attachment" "verdict_app" {
  role       = aws_iam_role.verdict_app.name
  policy_arn = aws_iam_policy.verdict_app.arn
}
