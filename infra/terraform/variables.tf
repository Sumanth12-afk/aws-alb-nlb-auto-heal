variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "target_group_arns" {
  description = "List of ALB/NLB target group ARNs to monitor"
  type        = list(string)
  default     = []
}

variable "monitoring_interval_minutes" {
  description = "Interval for target health monitoring (minutes)"
  type        = number
  default     = 5
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "slack_channel" {
  description = "Slack channel for notifications (e.g., #general)"
  type        = string
  default     = "#general"
}

variable "slack_username" {
  description = "Slack username for bot messages"
  type        = string
  default     = "Auto-Heal Bot"
}

variable "teams_webhook_url" {
  description = "Microsoft Teams webhook URL for notifications (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "health_check_endpoint" {
  description = "Application health check endpoint path"
  type        = string
  default     = "/health"
}

variable "health_check_port" {
  description = "Application health check port"
  type        = string
  default     = "80"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "enable_vpc" {
  description = "Enable VPC configuration for Lambda functions"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC ID for Lambda functions (if enable_vpc is true)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for Lambda functions (if enable_vpc is true)"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for Lambda functions (if enable_vpc is true)"
  type        = list(string)
  default     = []
}

variable "event_bus_name" {
  description = "EventBridge custom event bus name"
  type        = string
  default     = "default"
}

variable "dynamodb_ttl_days" {
  description = "TTL in days for DynamoDB tables"
  type        = number
  default     = 90
}

