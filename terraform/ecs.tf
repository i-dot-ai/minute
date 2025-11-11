locals {
  backend_port  = 8080
  frontend_port = 8081

  additional_policy_arns = { for idx, arn in [aws_iam_policy.ecs_exec_custom_policy.arn] : idx => arn }

  MAX_TRANSCRIPTION_PROCESSES = terraform.workspace == "prod" ? 4 : 2
  MAX_LLM_PROCESSES           = terraform.workspace == "prod" ? 8 : 4

  shared_environment_variables = {
    "ENVIRONMENT" : terraform.workspace,
    "PORT" : local.backend_port,
    "REPO" : "minute",
    "APP_URL" : aws_route53_record.type_a_record.fqdn,
    "AWS_ACCOUNT_ID" : data.aws_caller_identity.current.account_id,
    "DOCKER_BUILDER_CONTAINER" : "minute",
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "AUTH_PROVIDER_PUBLIC_KEY" : data.aws_ssm_parameter.auth_provider_public_key.value,
    "AZURE_OPENAI_API_VERSION" : "2024-10-21"
    "TRANSCRIPTION_QUEUE_NAME" : aws_sqs_queue.transcription_queue.name
    "TRANSCRIPTION_DEADLETTER_QUEUE_NAME" : aws_sqs_queue.transcription_queue_deadletter.name
    "LLM_QUEUE_NAME" : aws_sqs_queue.llm_queue.name
    "LLM_DEADLETTER_QUEUE_NAME" : aws_sqs_queue.llm_queue_deadletter.name
    "TRANSCRIPTION_SERVICES" : "[\"azure_stt_synchronous\",\"azure_stt_batch\"]"
    "MAX_TRANSCRIPTION_PROCESSES" : local.MAX_TRANSCRIPTION_PROCESSES
    "MAX_LLM_PROCESSES" : local.MAX_LLM_PROCESSES
    "AZURE_TRANSCRIPTION_CONTAINER_NAME" : "transcriptions"
    "FAST_LLM_PROVIDER"   = "gemini"
    "FAST_LLM_MODEL_NAME" = "gemini-2.5-flash-lite"
    "BEST_LLM_PROVIDER"   = "gemini"
    "BEST_LLM_MODEL_NAME" = "gemini-2.5-flash"
  }

}

module "backend" {
  name = "${local.name}-backend"

  # checkov:skip=CKV_SECRET_4:Skip secret check as these have to be used within the Github Action
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source                      = "../../i-dot-ai-core-terraform-modules//modules/ecs" # For testing local changes
  source                       = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v5.7.0-ecs"
  image_tag                    = var.image_tag
  ecr_repository_uri           = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/minute-backend"
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  host                         = local.host_backend
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ecs_cluster_id               = data.terraform_remote_state.platform.outputs.ecs_cluster_id
  ecs_cluster_name             = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  task_additional_iam_policies = local.additional_policy_arns
  certificate_arn              = data.terraform_remote_state.universal.outputs.certificate_arn
  target_group_name_override   = "minute-backend-${var.env}-tg"
  permissions_boundary_name    = "infra/i-dot-ai-${var.env}-minute-perms-boundary-app"

  https_listener_arn            = module.frontend.https_listener_arn
  service_discovery_service_arn = aws_service_discovery_service.service_discovery_service.arn
  create_networking             = false
  create_listener               = false

  additional_security_group_ingress = [
    {
      purpose          = "Frontend to backend container port"
      port             = local.backend_port
      additional_sg_id = module.frontend.ecs_sg_id
    }
  ]

  environment_variables = merge(local.shared_environment_variables, {
    "APP_NAME" : "${local.name}-backend"
  })

  secrets = [
    for k, v in aws_ssm_parameter.env_secrets : {
      name      = regex("([^/]+$)", v.arn)[0], # Extract right-most string (param name) after the final slash
      valueFrom = v.arn
    }
  ]

  container_port = local.backend_port
  memory         = terraform.workspace == "prod" ? 8192 : 4096
  cpu            = terraform.workspace == "prod" ? 4096 : 2048

  http_healthcheck = false
  container_healthcheck = {
    command     = ["CMD-SHELL", "curl --fail http://localhost:8080/healthcheck"]
    interval    = 60
    retries     = 3
    startPeriod = 30
    timeout     = 5
  }
}

module "frontend" {
  # checkov:skip=CKV_SECRET_4:Skip secret check as these have to be used within the Github Action
  name = "${local.name}-frontend"
  # source = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/ecs" # For testing local changes
  source                       = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v5.4.0-ecs"
  image_tag                    = var.image_tag
  ecr_repository_uri           = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/minute-frontend"
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  host                         = local.host
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ecs_cluster_id               = data.terraform_remote_state.platform.outputs.ecs_cluster_id
  ecs_cluster_name             = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  create_listener              = true
  certificate_arn              = data.terraform_remote_state.universal.outputs.certificate_arn
  target_group_name_override   = "minute-frontend-${var.env}-tg"
  task_additional_iam_policies = local.additional_policy_arns
  permissions_boundary_name    = "infra/i-dot-ai-${var.env}-minute-perms-boundary-app"

  environment_variables = {
    "ENVIRONMENT" : terraform.workspace,
    "APP_NAME" : "${local.name}-frontend"
    "PORT" : local.frontend_port,
    "REPO" : "minute",
    "BACKEND_HOST" : "http://${aws_service_discovery_service.service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}:${local.backend_port}"
    "AUTH_PROVIDER_PUBLIC_KEY" : data.aws_ssm_parameter.auth_provider_public_key.value,
  }

  secrets = [
    for k, v in aws_ssm_parameter.env_secrets : {
      name      = regex("([^/]+$)", v.arn)[0], # Extract right-most string (param name) after the final slash
      valueFrom = v.arn
    }
  ]

  container_port = local.frontend_port
  memory         = terraform.workspace == "prod" ? 2048 : 1024
  cpu            = terraform.workspace == "prod" ? 1024 : 512

  health_check = {
    accepted_response   = 200
    path                = "/health"
    interval            = 60
    timeout             = 70
    healthy_threshold   = 2
    unhealthy_threshold = 5
    port                = local.frontend_port
  }
  authenticate_keycloak = {
    enabled : true,
    realm_name : data.terraform_remote_state.keycloak.outputs.realm_name,
    client_id : var.project_name,
    client_secret : data.aws_ssm_parameter.client_secret.value,
    keycloak_dns : data.terraform_remote_state.keycloak.outputs.keycloak_dns
  }
}

module "worker" {
  name = "${local.name}-worker"

  # checkov:skip=CKV_SECRET_4:Skip secret check as these have to be used within the Github Action
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source                       = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v5.7.0-ecs"
  desired_app_count            = terraform.workspace == "prod" ? 2 : 1
  image_tag                    = var.image_tag
  ecr_repository_uri           = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/minute-worker"
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ecs_cluster_id               = data.terraform_remote_state.platform.outputs.ecs_cluster_id
  ecs_cluster_name             = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  task_additional_iam_policies = local.additional_policy_arns
  certificate_arn              = data.terraform_remote_state.universal.outputs.certificate_arn
  target_group_name_override   = "minute-worker-${var.env}-tg"
  permissions_boundary_name    = "infra/i-dot-ai-${var.env}-minute-perms-boundary-app"

  create_networking = false
  create_listener   = false

  environment_variables = merge(local.shared_environment_variables, {
    "APP_NAME" : "${local.name}-worker"
  })

  secrets = [
    for k, v in aws_ssm_parameter.env_secrets : {
      name      = regex("([^/]+$)", v.arn)[0], # Extract right-most string (param name) after the final slash
      valueFrom = v.arn
    }
  ]

  memory = terraform.workspace == "prod" ? 8192 : 4096
  cpu    = terraform.workspace == "prod" ? 4096 : 2048

  http_healthcheck = false
  container_healthcheck = {
    command     = ["CMD-SHELL", "poetry run python worker/healthcheck.py"]
    interval    = 60
    retries     = 3
    startPeriod = 60
    timeout     = 5
  }
}

resource "aws_service_discovery_private_dns_namespace" "private_dns_namespace" {
  name        = "${local.name}-internal"
  description = "${local.name} private dns namespace"
  vpc         = data.terraform_remote_state.vpc.outputs.vpc_id
}

resource "aws_service_discovery_service" "service_discovery_service" {
  name = "${local.name}-backend"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.private_dns_namespace.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

module "sns_topic" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source        = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/cloudwatch-slack-integration?ref=v2.0.1-cloudwatch-slack-integration"
  name          = local.name
  slack_webhook = data.aws_secretsmanager_secret_version.platform_slack_webhook.secret_string

  permissions_boundary_name = "infra/i-dot-ai-${var.env}-minute-perms-boundary-app"
}
module "backend-ecs-alarm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source           = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/ecs-alarms?ref=v1.0.1-ecs-alarms"
  name             = "${local.name}-backend"
  ecs_service_name = module.backend.ecs_service_name
  ecs_cluster_name = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  sns_topic_arn    = [module.sns_topic.sns_topic_arn]
}

module "frontend-ecs-alarm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source           = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/ecs-alarms?ref=v1.0.1-ecs-alarms"
  name             = "${local.name}-frontend"
  ecs_service_name = module.frontend.ecs_service_name
  ecs_cluster_name = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  sns_topic_arn    = [module.sns_topic.sns_topic_arn]
}

module "backend-alb-alarm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source        = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/alb-alarms?ref=v1.1.0-alb-alarms"
  name          = "${local.name}-backend"
  alb_arn       = module.load_balancer.alb_arn
  target_group  = module.backend.aws_lb_target_group_name
  sns_topic_arn = [module.sns_topic.sns_topic_arn]
}

module "frontend-alb-alarm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source        = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/observability/alb-alarms?ref=v1.1.0-alb-alarms"
  name          = "${local.name}-frontend"
  alb_arn       = module.load_balancer.alb_arn
  target_group  = module.frontend.aws_lb_target_group_name
  sns_topic_arn = [module.sns_topic.sns_topic_arn]
}
