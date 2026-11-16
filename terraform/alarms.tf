module "minute-db-alarm" {
  # checkov:skip=CKV_TF_1: Semver instead of commit hash
  source         = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/rds-alarms?ref=v1.0.0-rds-alarms"
  name           = "${local.name}-db"
  sns_topic_arns = [module.sns_topic.sns_topic_arn]

  rds_metadata = {
    engine                 = "aurora-postgresql"
    is_aurora              = true
    db_instance_identifier = "${local.name}-db-0"
    db_cluster_identifier  = "${local.name}-db"
    aurora_instance_count  = 1
  }
}

locals {
  emf_namespace = "Minute/Temporal"

  pipeline_alarms = {
    transcription     = { failure_rate = 0.5, max_age_seconds = 3600 }
    minute_generation = { failure_rate = 0.5, max_age_seconds = 900 }
    ai_edit           = { failure_rate = 0.5, max_age_seconds = 900 }
  }
}

resource "aws_cloudwatch_metric_alarm" "temporal_failure_rate" {
  for_each = local.pipeline_alarms

  alarm_name          = "${local.name}-temporal-${each.key}-high-failure-rate-alarm"
  alarm_description   = "Temporal ${each.key} failure rate averaged over 15 minutes exceeded ${each.value.failure_rate}."
  namespace           = local.emf_namespace
  metric_name         = "FailureRate"
  statistic           = "Average"
  comparison_operator = "GreaterThanThreshold"
  threshold           = each.value.failure_rate
  period              = 300
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  treat_missing_data  = "notBreaching"

  dimensions = {
    Environment = terraform.workspace
    Component   = each.key
  }

  alarm_actions = [module.sns_topic.sns_topic_arn]
  ok_actions    = [module.sns_topic.sns_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "temporal_in_progress_age" {
  for_each = local.pipeline_alarms

  alarm_name          = "${local.name}-temporal-${each.key}-stuck-workflow-alarm"
  alarm_description   = "Temporal ${each.key} has a workflow running longer than ${each.value.max_age_seconds}s for >10 minutes."
  namespace           = local.emf_namespace
  metric_name         = "InProgressMaxAgeSeconds"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = each.value.max_age_seconds
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "notBreaching"

  dimensions = {
    Environment = terraform.workspace
    Component   = each.key
  }

  alarm_actions = [module.sns_topic.sns_topic_arn]
  ok_actions    = [module.sns_topic.sns_topic_arn]
}
