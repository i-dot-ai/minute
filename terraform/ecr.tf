locals {
  # Worker services that each build and push their own image. These must match the
  # `service` names used by the CI build workflow (minute-<service>) and the
  # ecr_repository_uri values referenced by the ECS modules below.
  worker_ecr_repositories = [
    "${var.project_name}-audio-worker",
    "${var.project_name}-worker-transcription",
    "${var.project_name}-worker-summary",
  ]
}

resource "aws_ecr_repository" "worker" {
  for_each = toset(local.worker_ecr_repositories)

  name                 = each.value
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = data.terraform_remote_state.platform.outputs.kms_key_arn
  }
}
