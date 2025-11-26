output "target_monitor_lambda_arn" {
  description = "ARN of target monitor Lambda function"
  value       = aws_lambda_function.target_monitor.arn
}

output "diagnostics_lambda_arn" {
  description = "ARN of diagnostics Lambda function"
  value       = aws_lambda_function.diagnostics.arn
}

output "auto_heal_lambda_arn" {
  description = "ARN of auto-heal Lambda function"
  value       = aws_lambda_function.auto_heal.arn
}

output "verify_lambda_arn" {
  description = "ARN of verify Lambda function"
  value       = aws_lambda_function.verify.arn
}

output "sns_topic_arn" {
  description = "ARN of SNS topic for notifications"
  value       = aws_sns_topic.notifications.arn
}

output "event_bus_arn" {
  description = "ARN of EventBridge event bus"
  value       = var.event_bus_name == "default" ? "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:event-bus/default" : aws_cloudwatch_event_bus.auto_heal[0].arn
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    target_health_events = aws_dynamodb_table.target_health_events.name
    diagnostics_history = aws_dynamodb_table.diagnostics_history.name
    auto_heal_history   = aws_dynamodb_table.auto_heal_history.name
    instance_config     = aws_dynamodb_table.instance_config.name
    verification_history = aws_dynamodb_table.verification_history.name
  }
}

data "aws_caller_identity" "current" {}

