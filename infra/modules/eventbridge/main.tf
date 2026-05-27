# EventBridge rule: trigger ECS Fargate task at 17:00 IST Mon–Fri.
# 17:00 IST = 11:30 UTC (IST = UTC+5:30).

resource "aws_cloudwatch_event_rule" "daily_close" {
  name                = "${var.name_prefix}-daily-close"
  description         = "Trigger NSE LLM Trader daily run at 17:00 IST (11:30 UTC) Mon–Fri"
  schedule_expression = "cron(30 11 ? * MON-FRI *)"
  state               = "ENABLED"

  tags = {
    Name = "${var.name_prefix}-daily-trigger"
  }
}

# IAM role for EventBridge to launch ECS tasks

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_role" "eventbridge_ecs" {
  name = "${var.name_prefix}-eventbridge-ecs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_run_task" {
  name = "run-ecs-task"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [var.task_def_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [var.task_role_arn]
      }
    ]
  })
}

# VPC networking — uses default VPC for Phase 1 (cost-free; upgrade in Phase 2)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_cloudwatch_event_target" "run_task" {
  rule     = aws_cloudwatch_event_rule.daily_close.name
  arn      = var.cluster_arn
  role_arn = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = var.task_def_arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = data.aws_subnets.default.ids
      assign_public_ip = true  # required for Fargate in public subnet to reach ECR/APIs
      security_groups  = []    # uses default VPC security group
    }
  }

  # Route failed task launches to SNS
  dead_letter_config {
    arn = var.sns_topic_arn
  }
}
