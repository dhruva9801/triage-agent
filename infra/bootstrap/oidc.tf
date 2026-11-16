# GitHub Actions authenticates to AWS with short-lived OIDC tokens.
# No AWS access keys are ever stored in GitHub.
#
# Two roles:
#   plan   read-only; any branch or PR in this repo may assume it.
#   deploy can change infrastructure; ONLY the main branch may assume it.

locals {
  github_oidc = "token.actions.githubusercontent.com"
}

# One GitHub provider per AWS account. If your account already has one, import
# it instead of creating a second: see docs/setup.md, troubleshooting.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://${local.github_oidc}"
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's certificate against its own trusted CA library and
  # does not rely on these, but some provider versions still require the field.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

# ---- plan role --------------------------------------------------------------

data "aws_iam_policy_document" "plan_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc}:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "${local.github_oidc}:sub"
      values   = ["${var.github_sub_prefix}:*"]
    }
  }
}

resource "aws_iam_role" "plan" {
  name               = "${var.project}-github-plan"
  assume_role_policy = data.aws_iam_policy_document.plan_trust.json
}

# Trade-off, stated plainly: ReadOnlyAccess can read data too (S3 objects,
# DynamoDB items). Terraform's refresh needs broad Describe/Get/List, and
# writing a precise read policy is a rabbit hole for a solo project. Fork PRs
# cannot get OIDC tokens, so only collaborators can use this role.
resource "aws_iam_role_policy_attachment" "plan_readonly" {
  role       = aws_iam_role.plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# ---- deploy role ------------------------------------------------------------

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc}:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Exact match on main. NOTE: if a workflow job declares `environment:`,
    # GitHub changes the sub claim to <prefix>:environment:NAME and this
    # condition stops matching. Update both together.
    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc}:sub"
      values   = ["${var.github_sub_prefix}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${var.project}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
}

# PowerUserAccess: everything except IAM, Organizations and Account. The
# deploy role still needs to create the workloads' IAM roles; that is granted
# separately below, fenced by a permissions boundary.
resource "aws_iam_role_policy_attachment" "deploy_poweruser" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}
