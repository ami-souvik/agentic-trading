output "ecr_repository_url" {
  value = aws_ecr_repository.trader.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.trader.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.trader.arn
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.daily_run.arn
}

output "task_execution_role_arn" {
  value = aws_iam_role.ecs_execution_role.arn
}

output "task_role_arn" {
  value = aws_iam_role.ecs_task_role.arn
}
