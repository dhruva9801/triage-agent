terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.60.0, < 7.0.0"
    }
  }

  # Bucket and region are supplied at init time so no account-specific value
  # is hardcoded:
  #   terraform init -backend-config="bucket=<tf_state_bucket>" -backend-config="region=<region>"
  backend "s3" {
    key          = "main/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "main"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  # Created in infra/bootstrap. Every role here MUST carry it, or the deploy
  # role is not allowed to create the role at all.
  boundary_arn = "arn:aws:iam::${local.account_id}:policy/${var.project}-workload-boundary"
}
