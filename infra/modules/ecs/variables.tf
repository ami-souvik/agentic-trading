variable "name_prefix" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cpu" {
  type    = number
  default = 1024
}

variable "memory" {
  type    = number
  default = 2048
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "log_group_name" {
  type = string
}

variable "s3_bucket_arn" {
  type = string
}

variable "dynamo_table_arns" {
  type = list(string)
}

variable "llm_secret_arn" {
  type = string
}

variable "broker_secret_arn" {
  type = string
}
