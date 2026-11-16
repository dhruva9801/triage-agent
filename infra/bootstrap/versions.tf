# Bootstrap: resources that must exist before CI can run Terraform.
# Applied ONCE, by hand, with local state (this config creates the remote
# state bucket, so it cannot keep its own state there).
# See docs/setup.md, step 3.

terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.60.0, < 7.0.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}
