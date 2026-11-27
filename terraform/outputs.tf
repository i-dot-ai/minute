output "temporal_dependencies" {
  description = "Stable application infrastructure consumed by the independently released Temporal server."
  value = {
    namespace_id              = aws_service_discovery_private_dns_namespace.private_dns_namespace.id
    alb_arn                   = module.load_balancer.alb_arn
    alb_security_group_id     = module.load_balancer.load_balancer_security_group_id
    backend_security_group_id = module.backend.ecs_sg_id
    worker_security_group_id  = module.worker.ecs_sg_id
    sns_topic_arn             = module.sns_topic.sns_topic_arn
  }
}
