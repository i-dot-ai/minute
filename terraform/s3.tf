data "aws_iam_policy_document" "app_bucket" {
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetBucketLocation",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::i-dot-ai-${var.env}-minute-data",
      "arn:aws:s3:::i-dot-ai-${var.env}-minute-data/*",
    ]
    principals {
      type = "Service"
      identifiers = [
        "transcribe.amazonaws.com"
      ]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values = [
        data.aws_caller_identity.current.account_id,
      ]
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "cors" {
  bucket = module.app_bucket.id

  expected_bucket_owner = data.aws_caller_identity.current.account_id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET", "POST"]
    allowed_origins = ["https://${aws_route53_record.type_a_record.name}", "http://localhost:3000"]
    max_age_seconds = 3000
  }
}

module "app_bucket" {
  # checkov:skip=CKV_SECRET_4:Skip secret check as these have to be used within the Github Action
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source       = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/s3" # For testing local changes
  source        = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/s3?ref=v3.0.0-s3"
  name          = "${local.name}-data"
  log_bucket    = data.terraform_remote_state.platform.outputs.log_bucket
  kms_key       = data.terraform_remote_state.platform.outputs.kms_key_arn
  force_destroy = var.env == "dev" ? true : false

  default_policy_document = data.aws_iam_policy_document.app_bucket.json

  bucket_versioning_status = "Suspended"
}
