# Release-only admin tasks have no ECS service and never run during server restarts.
resource "aws_security_group" "temporal_admin" {
  name        = "${local.name}-temporal-admin-sg"
  description = "One-off Temporal release tasks"
  vpc_id      = data.terraform_remote_state.vpc.outputs.vpc_id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "random_password" "temporal_runtime" {
  length  = 40
  special = false
}

resource "aws_ssm_parameter" "temporal_runtime_password" {
  name   = "/${local.name}/env_secrets/TEMPORAL_RUNTIME_PASSWORD"
  type   = "SecureString"
  key_id = data.terraform_remote_state.platform.outputs.kms_key_arn
  value  = random_password.temporal_runtime.result
}

# The server's execution role can retrieve only runtime credentials, never the master password.
resource "aws_iam_policy" "temporal_runtime_secrets" {
  name = "${local.name}-temporal-runtime-secrets"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters"]
        Resource = [aws_ssm_parameter.temporal_runtime_password.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.terraform_remote_state.platform.outputs.kms_key_arn]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "temporal_admin" {
  name              = "/ecs/${local.name}-temporal-admin"
  retention_in_days = 90
}

resource "aws_iam_role" "temporal_admin" {
  name                 = "${local.name}-temporal-admin-role"
  permissions_boundary = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/infra/i-dot-ai-${var.env}-minute-perms-boundary-app"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "temporal_admin_execution" {
  role       = aws_iam_role.temporal_admin.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "temporal_admin_secrets" {
  role = aws_iam_role.temporal_admin.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters"]
        Resource = [aws_ssm_parameter.temporal_db_password.arn, aws_ssm_parameter.temporal_runtime_password.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [data.terraform_remote_state.platform.outputs.kms_key_arn]
      }
    ]
  })
}

resource "aws_ecs_task_definition" "temporal_admin" {
  family                   = "${local.name}-temporal-admin"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.temporal_admin.arn
  container_definitions = jsonencode([{
    name      = "temporal-admin"
    image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com/minute-temporal-admin:${var.image_tag}"
    essential = true
    environment = [
      { name = "POSTGRES_SEEDS", value = module.temporal_db.db_instance_address },
      { name = "POSTGRES_USER", value = module.temporal_db.rds_instance_username },
      { name = "DB_PORT", value = "5432" },
      { name = "SQL_TLS", value = "true" },
      { name = "SQL_TLS_DISABLE_HOST_VERIFICATION", value = "true" },
      { name = "TEMPORAL_ADDRESS", value = "temporal.${local.name}-internal:7233" }
    ]
    secrets = [
      { name = "POSTGRES_PWD", valueFrom = aws_ssm_parameter.temporal_db_password.arn },
      { name = "TEMPORAL_RUNTIME_PASSWORD", valueFrom = aws_ssm_parameter.temporal_runtime_password.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.temporal_admin.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "release"
      }
    }
  }])
  depends_on = [module.temporal_db, aws_security_group.temporal_admin, aws_iam_role_policy.temporal_admin_secrets, aws_iam_role_policy_attachment.temporal_admin_execution]
}

data "aws_security_group" "temporal_database" {
  name       = "${local.name}-temporal-db-rds-db-sg"
  depends_on = [module.temporal_db]
}

resource "aws_security_group_rule" "server_to_database" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = data.aws_security_group.temporal_database.id
  source_security_group_id = module.temporal.ecs_sg_id
}

output "temporal_admin" {
  value = {
    cluster         = data.terraform_remote_state.platform.outputs.ecs_cluster_id
    task_definition = aws_ecs_task_definition.temporal_admin.arn
    subnets         = data.terraform_remote_state.vpc.outputs.private_subnets
    security_group  = aws_security_group.temporal_admin.id
    log_group       = aws_cloudwatch_log_group.temporal_admin.name
    region          = var.region
  }
}
