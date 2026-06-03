output "s3_bucket_name" {
  value       = aws_s3_bucket.bootstrap_state.id
  description = "The name of the S3 bucket created for Terraform remote state storage"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.tflock.name
  description = "The name of the DynamoDB table created for Terraform state locking"
}

output "sns_topic_arn" {
  value       = module.budget.sns_topic_arn
  description = "The ARN of the SNS topic created for budget alerts"
}

