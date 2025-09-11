locals {
  # Add secrets to this list as required to make them available within the container.
  # Values must not be hardcoded here - they must either be references or updated in SSM Parameter Store.
  env_secrets = [
    {
      name  = "DATA_S3_BUCKET"
      value = module.app_bucket.id
    },
    {
      name  = "EXAMPLE_VAR"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_OPENAI_ENDPOINT"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_OPENAI_API_KEY"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_SPEECH_KEY"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_SPEECH_REGION"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "POSTGRES_PORT"
      value = 5432
    },
    {
      name  = "POSTGRES_DB"
      value = "minute_db"
    },
    {
      name  = "POSTGRES_USER"
      value = "postgres"
    },
    {
      name  = "POSTGRES_PASSWORD"
      value = module.rds.rds_instance_db_password
    },
    {
      name  = "SENTRY_DSN"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_DEPLOYMENT"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "GOOGLE_APPLICATION_CREDENTIALS_BASE64"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "GOOGLE_CLOUD_PROJECT"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "GOOGLE_CLOUD_LOCATION"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "AZURE_BLOB_CONNECTION_STRING"
      value = "placeholder" # Update value in SSM - Do not hardcode
    },
    {
      name  = "POSTHOG_API_KEY"
      value = "placeholder" # Update value in SSM - Do not hardcode
    }
  ]
}

resource "aws_ssm_parameter" "env_secrets" {
  for_each = { for ev in local.env_secrets : ev.name => ev }

  type   = "SecureString"
  key_id = data.terraform_remote_state.platform.outputs.kms_key_arn

  name  = "/${local.name}/env_secrets/${each.value.name}"
  value = each.value.value

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}
