output "ecr_repository_url" {
  description = "ECR repository URL — use in CI/CD for docker push"
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_task_definition_arn" {
  description = "Latest ECS task definition ARN"
  value       = module.ecs.task_definition_arn
}

output "dynamodb_table_names" {
  description = "Map of logical name → DynamoDB table name"
  value       = module.dynamodb.table_names
}

output "s3_bucket_name" {
  description = "S3 archive bucket name"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "S3 archive bucket ARN"
  value       = module.s3.bucket_arn
}

output "sns_alert_topic_arn" {
  description = "SNS topic ARN for circuit-breaker and cost alerts"
  value       = aws_sns_topic.alerts.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name for ECS task logs"
  value       = aws_cloudwatch_log_group.trader.name
}

output "eventbridge_rule_arn" {
  description = "EventBridge rule ARN that triggers the daily 17:00 IST run"
  value       = module.eventbridge.rule_arn
}

output "llm_secret_arn" {
  description = "Secrets Manager ARN for LLM API keys"
  value       = aws_secretsmanager_secret.llm_keys.arn
}
