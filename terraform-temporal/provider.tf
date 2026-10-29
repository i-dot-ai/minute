terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.5"
    }
  }

  required_version = ">= 1.7.0"

  backend "s3" {
    key = "minute-temporal/terraform.tfstate"
  }
}

provider "aws" {
  default_tags {
    tags = {
      "platform:repository"     = "${var.github_org}${var.repository_name}"
      "platform:environment"    = terraform.workspace
      "platform:deployed-via"   = var.deployed_via
      "platform:security-level" = var.security_level
      Organisation              = "co"
      Department                = "i-dot-ai"
      "Cost Centre"             = "i-dot-ai"
      BillingProject            = var.repository_name
    }
  }
}
