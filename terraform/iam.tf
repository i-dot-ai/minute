data "aws_iam_policy_document" "backend_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      module.app_bucket.arn,
      "${module.app_bucket.arn}/app_data/*",
      "${module.app_bucket.arn}/app_data",
      "${module.app_bucket.arn}/restricted/*",
      "${module.app_bucket.arn}/restricted",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      for name in local.backend_secret_names :
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${local.name}/env_secrets/${name}"
    ]
  }

  # Decrypt-only: the backend reads SSM SecureStrings and GETs/PUTs SSE-KMS S3 objects, but does
  # not perform standalone KMS encrypts. GenerateDataKey is required for S3 PutObject under SSE-KMS.
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [
      data.terraform_remote_state.platform.outputs.kms_key_arn,
    ]
  }
}

resource "aws_iam_policy" "backend_policy" {
  name        = "${local.name}-backend"
  description = "Backend ECS task policy (S3 object access, scoped SSM secrets, KMS)"
  policy      = data.aws_iam_policy_document.backend_policy.json
}

data "aws_iam_policy_document" "worker_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      module.app_bucket.arn,
      "${module.app_bucket.arn}/app_data/*",
      "${module.app_bucket.arn}/app_data",
      "${module.app_bucket.arn}/restricted/*",
      "${module.app_bucket.arn}/restricted",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      for name in local.worker_secret_names :
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${local.name}/env_secrets/${name}"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [
      data.terraform_remote_state.platform.outputs.kms_key_arn,
    ]
  }
}

resource "aws_iam_policy" "worker_policy" {
  name        = "${local.name}-worker"
  description = "Worker ECS task policy"
  policy      = data.aws_iam_policy_document.worker_policy.json
}
