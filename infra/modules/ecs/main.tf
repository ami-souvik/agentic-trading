# ECR repository, ECS cluster, task definition, and IAM roles.
# Fargate task: 1 vCPU / 2 GB. Runs once daily via EventBridge.

# ─── ECR ─────────────────────────────────────────────────────────────────────

resource "aws_ecr_repository" "trader" {
  name                 = var.name_prefix
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.name_prefix}-ecr"
  }
}

resource "aws_ecr_lifecycle_policy" "trader" {
  repository = aws_ecr_repository.trader.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only last 5 images to limit storage cost"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ─── ECS Cluster ─────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "trader" {
  name = var.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.name_prefix}-cluster"
  }
}

# ─── IAM: Task Execution Role (ECS agent) ────────────────────────────────────
# Used by ECS to: pull image from ECR, write to CloudWatch, fetch secrets.

resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.llm_secret_arn, var.broker_secret_arn]
    }]
  })
}

# ─── IAM: Task Role (application code at runtime) ────────────────────────────

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "task_dynamodb" {
  name = "dynamodb-access"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:BatchWriteItem",
      ]
      Resource = var.dynamo_table_arns
    }]
  })
}

resource "aws_iam_role_policy" "task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [var.s3_bucket_arn, "${var.s3_bucket_arn}/*"]
    }]
  })
}

resource "aws_iam_role_policy" "task_secrets" {
  name = "secrets-read"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.llm_secret_arn, var.broker_secret_arn]
    }]
  })
}

resource "aws_iam_role_policy" "task_cloudwatch" {
  name = "cloudwatch-logs"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${var.account_id}:*"
    }]
  })
}

# ─── ECS Task Definition ─────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "daily_run" {
  family                   = "${var.name_prefix}-daily-run"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "trader"
    image     = "${aws_ecr_repository.trader.repository_url}:${var.image_tag}"
    essential = true
    command   = ["python", "-m", "trader.daily_run"]

    environment = [
      { name = "AWS_REGION",           value = var.aws_region },
      { name = "PAPER_TRADING_MODE",   value = "true" },
      { name = "ENVIRONMENT",          value = "production" },
      { name = "LOG_LEVEL",            value = "INFO" },
    ]

    secrets = [
      { name = "ANTHROPIC_API_KEY", valueFrom = "${var.llm_secret_arn}:ANTHROPIC_API_KEY::" },
      { name = "GEMINI_API_KEY",    valueFrom = "${var.llm_secret_arn}:GEMINI_API_KEY::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "daily-run"
      }
    }

    healthCheck = null  # Batch task; no HTTP health check needed
  }])

  tags = {
    Name = "${var.name_prefix}-daily-run"
  }
}
