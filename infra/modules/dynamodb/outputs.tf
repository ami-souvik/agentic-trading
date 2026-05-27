output "table_name" {
  description = "Master DynamoDB table name"
  value       = aws_dynamodb_table.master.name
}

output "table_arn" {
  description = "Master DynamoDB table ARN (used in IAM policies)"
  value       = aws_dynamodb_table.master.arn
}

# Kept as a list so the ECS module interface stays unchanged
output "table_arns" {
  description = "List containing the master table ARN (for IAM policy attachment)"
  value       = [aws_dynamodb_table.master.arn]
}
