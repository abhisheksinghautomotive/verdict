data "aws_caller_identity" "current" {}

locals {
  common_tags = {
    Project     = "verdict"
    Environment = "bootstrap"
    ManagedBy   = "terraform"
    CostCenter  = "personal"
  }
}

resource "aws_s3_bucket" "bootstrap_state" {
  bucket        = "verdict-tfstate-${data.aws_caller_identity.current.account_id}"
  force_destroy = false

  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "bootstrap_state" {
  bucket = aws_s3_bucket.bootstrap_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bootstrap_state" {
  bucket = aws_s3_bucket.bootstrap_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "bootstrap_state" {
  bucket = aws_s3_bucket.bootstrap_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "verdict-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = local.common_tags
}

module "budget" {
  source = "../modules/budget"

  alert_email = var.alert_email
  common_tags = local.common_tags
}

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]

  tags = local.common_tags
}

resource "aws_iam_role" "gha_verdict_deploy" {
  name = "gha-verdict-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:abhisheksinghautomotive/verdict:*"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# The deployment role requires AdministratorAccess as it is used by the CI/CD pipeline
# to provision and destroy low-level infrastructure resources (VPC, EKS clusters, IAM roles, Security Groups, etc.) via Terraform.
# The risk is mitigated by scoping assumption strictly to the OIDC identity provider matching the specific GitHub repo.
resource "aws_iam_role_policy_attachment" "gha_verdict_deploy_admin" {
  role       = aws_iam_role.gha_verdict_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}


