terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment after first apply to store state in S3:
  # backend "s3" {
  #   bucket         = "nse-llm-trader-tfstate"
  #   key            = "dev/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "nse-llm-trader-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  name_prefix = "${var.project_name}-${var.environment}"
}

# ─── DynamoDB Tables ─────────────────────────────────────────────────────────

module "dynamodb" {
  source      = "./modules/dynamodb"
  table_name  = var.dynamo_table_name
  name_prefix = local.name_prefix
}

# ─── S3 Archive Bucket ───────────────────────────────────────────────────────

module "s3" {
  source                = "./modules/s3"
  bucket_name           = var.s3_bucket_name
  archive_retention_days = var.s3_archive_retention_days
  name_prefix           = local.name_prefix
}

# ─── ECR + ECS ───────────────────────────────────────────────────────────────

module "ecs" {
  source              = "./modules/ecs"
  name_prefix         = local.name_prefix
  aws_region          = var.aws_region
  account_id          = local.account_id
  cpu                 = var.ecs_cpu
  memory              = var.ecs_memory
  image_tag           = var.ecr_image_tag
  log_group_name      = aws_cloudwatch_log_group.trader.name
  s3_bucket_arn       = module.s3.bucket_arn
  dynamo_table_arns   = module.dynamodb.table_arns
  llm_secret_arn      = aws_secretsmanager_secret.llm_keys.arn
  broker_secret_arn   = aws_secretsmanager_secret.broker_keys.arn
}

# ─── EventBridge Rule — 17:00 IST = 11:30 UTC Mon–Fri ────────────────────────

module "eventbridge" {
  source           = "./modules/eventbridge"
  name_prefix      = local.name_prefix
  cluster_arn      = module.ecs.cluster_arn
  task_def_arn     = module.ecs.task_definition_arn
  task_role_arn    = module.ecs.task_execution_role_arn
  sns_topic_arn    = aws_sns_topic.alerts.arn
}

# ─── Secrets Manager ─────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "llm_keys" {
  name                    = "nse-trader/llm-keys"
  description             = "Anthropic and Gemini API keys for NSE LLM Trader"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-llm-keys"
  }
}

resource "aws_secretsmanager_secret_version" "llm_keys_placeholder" {
  secret_id = aws_secretsmanager_secret.llm_keys.id
  # Placeholder — update manually via AWS console or CLI before first run:
  # aws secretsmanager put-secret-value --secret-id nse-trader/llm-keys \
  #   --secret-string '{"ANTHROPIC_API_KEY":"sk-ant-...","GEMINI_API_KEY":"AIza..."}'
  secret_string = jsonencode({
    ANTHROPIC_API_KEY = "REPLACE_ME"
    GEMINI_API_KEY    = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]  # Don't overwrite manually-set secrets on re-apply
  }
}

resource "aws_secretsmanager_secret" "broker_keys" {
  name                    = "nse-trader/broker-keys"
  description             = "Zerodha Kite API keys (Phase 2 only — empty in Phase 1)"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-broker-keys"
  }
}

resource "aws_secretsmanager_secret_version" "broker_keys_placeholder" {
  secret_id = aws_secretsmanager_secret.broker_keys.id
  secret_string = jsonencode({
    KITE_API_KEY     = ""
    KITE_API_SECRET  = ""
    KITE_ACCESS_TOKEN = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ─── CloudWatch Log Group ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "trader" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name = "${local.name_prefix}-logs"
  }
}

# ─── SNS Alerts ──────────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = {
    Name = "${local.name_prefix}-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ─── CloudWatch Alarms ────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "ecs_task_failed" {
  alarm_name          = "${local.name_prefix}-task-failure"
  alarm_description   = "ECS daily run task failed"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FailedTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = module.ecs.cluster_name
  }
}
