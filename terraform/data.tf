data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "terraform_remote_state" "vpc" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "vpc/terraform.tfstate"
    region = var.region
  }
}


data "terraform_remote_state" "platform" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "platform/terraform.tfstate"
    region = var.region
  }
}


data "terraform_remote_state" "universal" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "universal/terraform.tfstate"
    region = var.region
  }
}

data "terraform_remote_state" "account" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "account/terraform.tfstate"
    region = var.region
  }
}

data "terraform_remote_state" "keycloak" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "core/keycloak/keycloak/terraform.tfstate"
    region = var.region
  }
}

locals {
  name              = "${var.team_name}-${var.env}-${var.project_name}"
  host              = terraform.workspace == "prod" ? "${var.project_name}.ai.cabinetoffice.gov.uk" : "${var.project_name}-${terraform.workspace}.ai.cabinetoffice.gov.uk"
  host_backend      = terraform.workspace == "prod" ? "${var.project_name}-backend-external.ai.cabinetoffice.gov.uk" : "${var.project_name}-backend-external-${terraform.workspace}.ai.cabinetoffice.gov.uk"
  record_prefix     = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  auth_from_address = "${local.record_prefix}@auth-notify.${var.domain_name}"
  auth_ses_identity = "arn:aws:ses:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:identity/auth-notify.ai.cabinetoffice.gov.uk"
}

data "aws_ssm_parameter" "auth_api_invoke_url" {
  name = "/i-dot-ai-${terraform.workspace}-core-auth-api/auth/INVOKE_URL"
}

data "aws_ssm_parameter" "client_secret" {
  name = "/${var.team_name}-${terraform.workspace}-core-keycloak/app_client_secret/${var.project_name}"
}

data "aws_ssm_parameter" "auth_provider_public_key" {
  name = "/i-dot-ai-${terraform.workspace}-core-keycloak/realm_public_key"
}

data "aws_secretsmanager_secret" "slack" {
  name = "i-dot-ai-${var.env}-platform-slack-webhook"
}

data "aws_secretsmanager_secret_version" "platform_slack_webhook" {
  secret_id = data.aws_secretsmanager_secret.slack.id
}
