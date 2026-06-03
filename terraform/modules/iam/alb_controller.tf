data "aws_iam_policy_document" "alb_controller_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
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

resource "aws_iam_role" "aws_load_balancer_controller" {
  name               = "aws-load-balancer-controller-irsa"
  assume_role_policy = data.aws_iam_policy_document.alb_controller_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "aws-load-balancer-controller-irsa"
    }
  )
}

resource "aws_iam_policy" "aws_load_balancer_controller" {
  name        = "aws-load-balancer-controller-policy"
  description = "IAM policy for the AWS Load Balancer Controller"
  policy      = file("${path.module}/aws_load_balancer_controller_policy.json")

  tags = merge(
    var.common_tags,
    {
      Name = "aws-load-balancer-controller-policy"
    }
  )
}

resource "aws_iam_role_policy_attachment" "aws_load_balancer_controller" {
  role       = aws_iam_role.aws_load_balancer_controller.name
  policy_arn = aws_iam_policy.aws_load_balancer_controller.arn
}
