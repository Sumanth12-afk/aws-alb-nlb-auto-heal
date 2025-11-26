# SNS Topic for notifications
resource "aws_sns_topic" "notifications" {
  name = "${var.environment}-auto-heal-notifications"
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-notifications"
  })
}

# SNS Topic Subscription (Email - optional)
# Uncomment and configure if needed
# resource "aws_sns_topic_subscription" "email" {
#   topic_arn = aws_sns_topic.notifications.arn
#   protocol  = "email"
#   endpoint  = "your-email@example.com"
# }

# SNS Topic Subscription (Slack - if webhook URL provided)
resource "aws_sns_topic_subscription" "slack" {
  count     = var.slack_webhook_url != "" ? 1 : 0
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_notifier[0].arn
}

# SNS Topic Subscription (Teams - if webhook URL provided)
# Note: Teams integration would require a Lambda function to format messages
# This is a placeholder - implement Teams integration Lambda if needed

