# Observability for the self-hosted Temporal server and its dedicated Aurora.

# The app and the Temporal server are separate TF roots and are released independently, the root
# app TF needs to be applied before Temporal. This precondition tries to make that a little 
# less cryptic if we get a missing-output error.
resource "terraform_data" "require_application_contract" {
  lifecycle {
    precondition {
      condition = alltrue([
        for v in [
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.namespace_id, ""),
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.alb_arn, ""),
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.alb_security_group_id, ""),
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.backend_security_group_id, ""),
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.worker_security_group_id, ""),
          try(data.terraform_remote_state.application.outputs.temporal_dependencies.sns_topic_arn, ""),
        ] : v != ""
      ])
      error_message = "App root (terraform/) outputs are missing or incomplete: Apply the application root first, then re-run the Temporal server deploy."
    }
  }
}

locals {
  sns_topic_arn = data.terraform_remote_state.application.outputs.temporal_dependencies.sns_topic_arn
}

module "temporal-db-alarm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source         = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/rds-alarms?ref=v1.0.0-rds-alarms"
  name           = "${local.name}-temporal-db"
  sns_topic_arns = [local.sns_topic_arn]

  rds_metadata = {
    engine                 = "aurora-postgresql"
    is_aurora              = true
    db_instance_identifier = "${local.name}-temporal-db-0"
    db_cluster_identifier  = "${local.name}-temporal-db"
    aurora_instance_count  = 1
  }
}

resource "aws_cloudwatch_metric_alarm" "temporal_server_no_running_tasks" {
  alarm_name          = "${local.name}-temporal-ecs-low-running-task-count-alarm"
  alarm_description   = "AVAILABILITY: Temporal server has no running ECS task for >5 minutes."
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  statistic           = "Minimum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 60
  evaluation_periods  = 5
  datapoints_to_alarm = 5
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = data.terraform_remote_state.platform.outputs.ecs_cluster_name
    ServiceName = module.temporal.ecs_service_name
  }

  alarm_actions = [local.sns_topic_arn]
  ok_actions    = [local.sns_topic_arn]
}
