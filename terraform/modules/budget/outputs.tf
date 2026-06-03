output "sns_topic_arn" {
  value       = aws_sns_topic.budget_alerts.arn
  description = "The ARN of the SNS topic created for budget alerts"
}
