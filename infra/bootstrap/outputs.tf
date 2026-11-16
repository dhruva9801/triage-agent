# Copy these into GitHub: Settings → Secrets and variables → Actions →
# Variables (NOT secrets; none of these values are secret).

output "aws_region" {
  value = var.aws_region
}

output "tf_state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}

output "plan_role_arn" {
  value = aws_iam_role.plan.arn
}

output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}

output "ecr_repository_urls" {
  value = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}

output "workload_boundary_arn" {
  value = aws_iam_policy.workload_boundary.arn
}
