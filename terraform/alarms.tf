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
  emf_namespace = "${var.project_name}/${terraform.workspace}"

  pipeline_alarms = {
    transcription     = { failure_rate_percent = 50, max_age_seconds = 3600 }
    minute_generation = { failure_rate_percent = 50, max_age_seconds = 900 }
    ai_edit           = { failure_rate_percent = 50, max_age_seconds = 900 }
  }
}

resource "aws_cloudwatch_metric_alarm" "temporal_failure_rate" {
  for_each = local.pipeline_alarms

  alarm_name          = "${local.name}-temporal-${each.key}-high-failure-rate-alarm"
  alarm_description   = "Temporal ${each.key} failure rate over a 5-minute window exceeded ${each.value.failure_rate_percent}%."
  comparison_operator = "GreaterThanThreshold"
  threshold           = each.value.failure_rate_percent
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "f"
    return_data = false

    metric {
      namespace   = local.emf_namespace
      metric_name = "temporal_${each.key}_failed"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "c"
    return_data = false

    metric {
      namespace   = local.emf_namespace
      metric_name = "temporal_${each.key}_completed"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "rate"
    expression  = "IF((f + c) > 0, 100 * f / (f + c))"
    label       = "temporal_${each.key}_failure_rate"
    return_data = true
  }

  alarm_actions = [module.sns_topic.sns_topic_arn]
  ok_actions    = [module.sns_topic.sns_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "temporal_in_progress_age" {
  for_each = local.pipeline_alarms

  alarm_name          = "${local.name}-temporal-${each.key}-stuck-workflow-alarm"
  alarm_description   = "Temporal ${each.key} has a workflow running longer than ${each.value.max_age_seconds}s for >5 minutes."
  namespace           = local.emf_namespace
  metric_name         = "temporal_${each.key}_in_progress_max_age_seconds"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = each.value.max_age_seconds
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [module.sns_topic.sns_topic_arn]
  ok_actions    = [module.sns_topic.sns_topic_arn]
}

# Above pipeline metrics treat missing data as notBreaching so workers could stop emitting 
# in error without triggering any alarms. This heartbeat closes that gap, and treats an 
# absence as breaching even if temporal in general is still up and "healthy"
resource "aws_cloudwatch_metric_alarm" "temporal_metrics_heartbeat" {
  alarm_name          = "${local.name}-temporal-metrics-heartbeat-missing-alarm"
  alarm_description   = "Temporal metrics heartbeat missing for >5 minutes: the scheduled metrics workflow has stopped emitting."
  namespace           = local.emf_namespace
  metric_name         = "temporal_metrics_heartbeat"
  statistic           = "Sum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "breaching"

  alarm_actions = [module.sns_topic.sns_topic_arn]
  ok_actions    = [module.sns_topic.sns_topic_arn]
}
