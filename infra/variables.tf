variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short project name used as a prefix for all resources"
  type        = string
  default     = "nse-llm-trader"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "alert_email" {
  description = "Email address for SNS circuit-breaker and cost alerts"
  type        = string
}

variable "dynamo_table_name" {
  description = "Master DynamoDB table name (must match DYNAMO_TABLE_NAME env var)"
  type        = string
  default     = "nse_trader"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for raw data archive and decision logs"
  type        = string
  default     = "nse-llm-trader-archive"
}

variable "ecr_image_tag" {
  description = "Docker image tag to deploy (updated by CI/CD)"
  type        = string
  default     = "latest"
}

variable "ecs_cpu" {
  description = "ECS Fargate task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "ECS Fargate task memory in MB"
  type        = number
  default     = 2048
}

variable "cloudwatch_log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "s3_archive_retention_days" {
  description = "Days before S3 objects are deleted (cost control)"
  type        = number
  default     = 90
}
