module "rds" {
  #   source = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/rds"  # For testing local changes
  source                 = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/rds?ref=v4.0.1-rds"
  db_name                = "${replace(var.project_name, "-", "_")}_db"
  kms_secrets_arn        = data.terraform_remote_state.platform.outputs.kms_key_arn
  name                   = "${local.name}-db"
  public_subnet_ids_list = data.terraform_remote_state.vpc.outputs.public_subnets
  service_sg_ids = [
    module.backend.ecs_sg_id,
    module.frontend.ecs_sg_id
  ]
  vpc_id                = data.terraform_remote_state.vpc.outputs.vpc_id
  engine                = "aurora-postgresql"
  engine_version        = "16.8"
  family                = null
  engine_mode           = "provisioned"
  aurora_min_scaling    = 0.5
  aurora_max_scaling    = 1
  aurora_instance_count = 1
  deletion_protection   = var.env == "dev" ? false : true
  env                   = var.env
}
