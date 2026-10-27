# Self-hosted Temporal. The backend starts workflows and the worker polls them, so both need a
# frontend they can reach in-VPC: it is registered under Cloud Map as `temporal.<namespace>:7233`
# and handed out via TEMPORAL_ADDRESS in the application's ecs.tf. This root has separate state.
#
# ponytail: one server container runs every role, and a single Aurora writer holds persistence. That
# is fine for dev and low volume. Before this carries real production load, split frontend/history/
# matching/worker into their own services and add replicas (and consider a separate visibility store).

# --- persistence: dedicated Aurora Postgres, same module as the app database ---
module "temporal_db" {
  source                  = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/rds?ref=v4.0.1-rds"
  db_name                 = "temporal"
  kms_secrets_arn         = data.terraform_remote_state.platform.outputs.kms_key_arn
  name                    = "${local.name}-temporal-db"
  public_subnet_ids_list  = data.terraform_remote_state.vpc.outputs.public_subnets
  service_sg_ids          = [aws_security_group.temporal_admin.id]
  vpc_id                  = data.terraform_remote_state.vpc.outputs.vpc_id
  engine                  = "aurora-postgresql"
  engine_version          = "16.11"
  family                  = null
  engine_mode             = "provisioned"
  aurora_min_scaling      = 0.5
  aurora_max_scaling      = 1
  aurora_instance_count   = 1
  deletion_protection     = var.env == "dev" ? false : true
  backup_retention_period = 35
  env                     = var.env
}

# The RDS module generates the master password, so surface it through SSM (under the prefix the task
# execution role may read) and inject it as a container secret rather than plain text.
resource "aws_ssm_parameter" "temporal_db_password" {
  name   = "/${local.name}/env_secrets/TEMPORAL_POSTGRES_PASSWORD"
  type   = "SecureString"
  key_id = data.terraform_remote_state.platform.outputs.kms_key_arn
  value  = module.temporal_db.rds_instance_db_password

  lifecycle {
    ignore_changes = [value]
  }
}

# --- service discovery so backend/worker resolve the frontend ---
resource "aws_service_discovery_service" "temporal" {
  name = "temporal"

  dns_config {
    namespace_id = data.terraform_remote_state.application.outputs.temporal_dependencies.namespace_id

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

# --- the server (frontend, history, matching and worker roles in one container) ---
module "temporal" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v7.0.1-ecs"

  name                       = "${local.name}-temporal"
  image_tag                  = var.image_tag
  ecr_repository_uri         = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/minute-temporal"
  container_port             = 7233
  cpu                        = var.env == "prod" ? 2048 : 1024
  memory                     = var.env == "prod" ? 4096 : 2048
  wait_for_ready_state       = true
  desired_app_count          = 1
  autoscaling_minimum_target = 1
  autoscaling_maximum_target = 1

  vpc_id                        = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets               = data.terraform_remote_state.vpc.outputs.private_subnets
  aws_lb_arn                    = data.terraform_remote_state.application.outputs.temporal_dependencies.alb_arn
  load_balancer_security_group  = data.terraform_remote_state.application.outputs.temporal_dependencies.alb_security_group_id
  certificate_arn               = data.terraform_remote_state.universal.outputs.certificate_arn
  target_group_name_override    = "minute-temporal-${var.env}-tg"
  ecs_cluster_id                = data.terraform_remote_state.platform.outputs.ecs_cluster_id
  ecs_cluster_name              = data.terraform_remote_state.platform.outputs.ecs_cluster_name
  task_additional_iam_policies  = { "0" = aws_iam_policy.temporal_runtime_secrets.arn }
  permissions_boundary_name     = "infra/i-dot-ai-${var.env}-minute-perms-boundary-app"
  service_discovery_service_arn = aws_service_discovery_service.temporal.arn

  create_networking = false
  create_listener   = false
  http_healthcheck  = false
  # Namespace registration is a post-deploy admin task; server readiness must not depend on it.
  container_healthcheck = {
    command     = ["CMD", "temporal", "operator", "cluster", "health", "--address", "localhost:7233"]
    interval    = 10
    retries     = 6
    startPeriod = 60
    timeout     = 5
  }

  # Let the app's services reach the frontend on 7233.
  additional_security_group_ingress = [
    {
      purpose          = "backend-to-temporal"
      port             = 7233
      additional_sg_id = data.terraform_remote_state.application.outputs.temporal_dependencies.backend_security_group_id
    },
    {
      purpose          = "worker-to-temporal"
      port             = 7233
      additional_sg_id = data.terraform_remote_state.application.outputs.temporal_dependencies.worker_security_group_id
    },
    {
      purpose          = "admin-to-temporal"
      port             = 7233
      additional_sg_id = aws_security_group.temporal_admin.id
    },
  ]

  # The running server cannot create databases or upgrade their schemas.
  environment_variables = {
    "DB"                = "postgres12"
    "DB_PORT"           = "5432"
    "POSTGRES_SEEDS"    = module.temporal_db.db_instance_address
    "POSTGRES_USER"     = "temporal_runtime"
    "DBNAME"            = "temporal"
    "VISIBILITY_DBNAME" = "temporal_visibility"
    # Bind the frontend on all interfaces so it is reachable over the Cloud Map address and loopback.
    "BIND_ON_IP" = "0.0.0.0"
    # Minimal dynamic config shipped in the image (see temporal/dynamicconfig/docker.yaml).
    "DYNAMIC_CONFIG_FILE_PATH" = "/etc/temporal/config/dynamicconfig/docker.yaml"
    # Aurora forces TLS (the RDS module sets rds.force_ssl=true). SQL_TLS_ENABLED is the server's
    # switch; SQL_TLS / SQL_TLS_DISABLE_HOST_VERIFICATION drive temporal-sql-tool. Host verification
    # is off (like the app's sslmode=prefer), so no RDS CA bundle is needed. Local Postgres has no
    # TLS, so these are set here, not in the image.
    "SQL_TLS_ENABLED"                   = "true"
    "SQL_TLS"                           = "true"
    "SQL_TLS_DISABLE_HOST_VERIFICATION" = "true"
  }

  secrets = [
    {
      name      = "POSTGRES_PWD"
      valueFrom = aws_ssm_parameter.temporal_runtime_password.arn
    }
  ]
}

# ECS rolling deployments overlap server tasks even with an autoscaling maximum of one.
resource "aws_security_group_rule" "temporal_internode" {
  for_each = toset(["6933", "6934", "6935", "6939", "7233", "7234", "7235", "7239"])

  type                     = "ingress"
  description              = "Temporal server-to-server communication"
  from_port                = tonumber(each.value)
  to_port                  = tonumber(each.value)
  protocol                 = "tcp"
  security_group_id        = module.temporal.ecs_sg_id
  source_security_group_id = module.temporal.ecs_sg_id
}
