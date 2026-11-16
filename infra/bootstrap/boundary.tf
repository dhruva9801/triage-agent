# Permissions boundary: the ceiling on what any workload role can ever do.
#
# Without it, the deploy role could create a role named triage-anything, attach
# AdministratorAccess, hand it to a Lambda it also creates, and escalate to
# full admin. With it, every role the deploy role creates MUST carry this
# boundary, and a role's effective permissions are the intersection of its own
# policies and the boundary. Whatever the workload policies say, they cannot
# exceed this list.
#
# When a feature needs an AWS action that is not listed here, widen THIS
# policy, by hand, in bootstrap. That is deliberate friction.

data "aws_iam_policy_document" "workload_boundary" {
  statement {
    sid    = "WorkloadServices"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "s3:GetObject",
      "s3:PutObject",
      "bedrock:InvokeModel",
      "bedrock:ApplyGuardrail",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "cloudwatch:PutMetricData",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "workload_boundary" {
  name        = "${var.project}-workload-boundary"
  description = "Ceiling on permissions for every ${var.project} workload role"
  policy      = data.aws_iam_policy_document.workload_boundary.json
}

locals {
  workload_role_arn_pattern = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-*"
}

data "aws_iam_policy_document" "deploy_iam" {
  # Create and modify workload roles, but only with the boundary attached.
  statement {
    sid    = "ManageWorkloadRolesWithBoundary"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:PutRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePermissionsBoundary",
    ]
    resources = [local.workload_role_arn_pattern]
    condition {
      test     = "StringEquals"
      variable = "iam:PermissionsBoundary"
      values   = [aws_iam_policy.workload_boundary.arn]
    }
  }

  # Housekeeping that cannot grant new permissions.
  statement {
    sid    = "ReadAndCleanUpWorkloadRoles"
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateRole",
      "iam:UpdateRoleDescription",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
    ]
    resources = [local.workload_role_arn_pattern]
  }

  # Hand workload roles only to Lambda.
  statement {
    sid       = "PassWorkloadRolesToLambda"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [local.workload_role_arn_pattern]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  # The deploy and plan roles also match triage-*. Never let the deploy role
  # touch itself, the plan role, or remove a boundary.
  statement {
    sid     = "ProtectPipelineRoles"
    effect  = "Deny"
    actions = ["iam:*"]
    resources = [
      aws_iam_role.deploy.arn,
      aws_iam_role.plan.arn,
    ]
  }
  statement {
    sid       = "NeverRemoveBoundaries"
    effect    = "Deny"
    actions   = ["iam:DeleteRolePermissionsBoundary"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy_iam" {
  name   = "manage-workload-roles"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_iam.json
}
