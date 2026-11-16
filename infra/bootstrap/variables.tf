variable "aws_region" {
  description = "Region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix for every resource. Workload IAM roles must start with it."
  type        = string
  default     = "triage"
}

# The part of the OIDC `sub` claim that identifies this repository. Repos
# created after July 2026 include immutable numeric IDs
# (repo:OWNER@OWNER_ID/REPO@REPO_ID); older repos use repo:OWNER/REPO.
# Copy the value GitHub reports rather than building it by hand:
#   gh api repos/OWNER/REPO/actions/oidc/customization/sub
variable "github_sub_prefix" {
  description = "OIDC subject prefix GitHub issues for this repository."
  type        = string

  # A wildcard here would let other repositories assume the deploy role.
  validation {
    condition     = can(regex("^repo:[^*?:]+/[^*?:]+$", var.github_sub_prefix))
    error_message = "Must look like repo:OWNER@ID/REPO@ID (or repo:OWNER/REPO), with no wildcards."
  }
}
