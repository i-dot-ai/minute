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

  statement {
    effect = "Allow"
    actions = [
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
      "sqs:SendMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [
      aws_sqs_queue.transcription_queue.arn,
      aws_sqs_queue.transcription_queue_deadletter.arn,
      aws_sqs_queue.llm_queue.arn,
      aws_sqs_queue.llm_queue_deadletter.arn
    ]
  }
}

resource "aws_iam_policy" "ecs_exec_custom_policy" {
  name        = "${local.name}-ecs-custom-exec"
  description = "ECS task custom policy"
  policy      = data.aws_iam_policy_document.ecs_exec_custom_policy.json
}
