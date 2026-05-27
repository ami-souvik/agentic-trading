variable "bucket_name" {
  description = "S3 bucket name for raw data archive and decision logs"
  type        = string
}

variable "archive_retention_days" {
  description = "Days before objects are deleted via lifecycle rule"
  type        = number
  default     = 90
}

variable "name_prefix" {
  description = "Resource name prefix for tags"
  type        = string
}
