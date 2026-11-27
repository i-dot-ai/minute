data "aws_iam_policy_document" "ecs_exec_custom_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:Get*",
      "s3:List*",
      "s3:Put*",
      "s3:Delete*",
    ]
    resources = [
      "${module.app_bucket.arn}/app_data/*",
      "${module.app_bucket.arn}/app_data",
      "${module.app_bucket.arn}/restricted/*",
      "${module.app_bucket.arn}/restricted",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "transcribe:GetTranscriptionJob",
      "transcribe:StartTranscriptionJob",
    ]
    resources = [
      "arn:aws:transcribe:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:transcription-job/minute-*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    # Cross-region inference needs both: the profile in this account and region, and the foundation
    # model in whichever EU region the profile routes the request to.
    resources = [
      "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/${local.bedrock_inference_profile_id}",
      "arn:aws:bedrock:*::foundation-model/${local.bedrock_foundation_model_id}",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${local.name}/env_secrets/*"
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

resource "aws_iam_policy" "ecs_exec_custom_policy" {
  name        = "${local.name}-ecs-custom-exec"
  description = "ECS task custom policy"
  policy      = data.aws_iam_policy_document.ecs_exec_custom_policy.json
}
