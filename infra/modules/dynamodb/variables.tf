variable "table_name" {
  description = "Master DynamoDB table name (e.g. 'nse_trader')"
  type        = string
}

variable "name_prefix" {
  description = "Resource name prefix for tags (e.g. 'nse-llm-trader-dev')"
  type        = string
}
