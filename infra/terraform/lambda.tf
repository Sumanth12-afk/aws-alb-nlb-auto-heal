# Lambda layer for shared utilities
# Lambda layers require python/ directory structure
data "archive_file" "utils_layer" {
  type        = "zip"
  output_path = "${path.module}/lambda_utils_layer.zip"
  
  source {
    content  = file("${path.module}/../../src/lambda/utils/__init__.py")
    filename = "python/utils/__init__.py"
  }
  
  source {
    content  = file("${path.module}/../../src/lambda/utils/aws_clients.py")
    filename = "python/utils/aws_clients.py"
  }
  
  source {
    content  = file("${path.module}/../../src/lambda/utils/logger.py")
    filename = "python/utils/logger.py"
  }
  
  source {
    content  = file("${path.module}/../../src/lambda/utils/helpers.py")
    filename = "python/utils/helpers.py"
  }
}

resource "aws_lambda_layer_version" "utils" {
  filename            = data.archive_file.utils_layer.output_path
  layer_name          = "${var.environment}-auto-heal-utils"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = data.archive_file.utils_layer.output_base64sha256
}

# Target Monitor Lambda
data "archive_file" "target_monitor" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/target_monitor"
  output_path = "${path.module}/target_monitor.zip"
}

resource "aws_lambda_function" "target_monitor" {
  filename         = data.archive_file.target_monitor.output_path
  function_name    = "${var.environment}-auto-heal-target-monitor"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  source_code_hash = data.archive_file.target_monitor.output_base64sha256
  
  layers = [aws_lambda_layer_version.utils.arn]
  
  environment {
    variables = {
      TARGET_HEALTH_TABLE = aws_dynamodb_table.target_health_events.name
      DIAGNOSTICS_TABLE   = aws_dynamodb_table.diagnostics_history.name
      EVENT_BUS_NAME      = var.event_bus_name
      TARGET_GROUP_ARNS    = join(",", var.target_group_arns)
    }
  }
  
  vpc_config {
    subnet_ids         = var.enable_vpc ? var.subnet_ids : []
    security_group_ids = var.enable_vpc ? var.security_group_ids : []
  }
  
  depends_on = [
    aws_cloudwatch_log_group.target_monitor,
    aws_iam_role_policy_attachment.lambda_execution
  ]
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-target-monitor"
  })
}

resource "aws_cloudwatch_log_group" "target_monitor" {
  name              = "/aws/lambda/${var.environment}-auto-heal-target-monitor"
  retention_in_days = 14
  
  tags = local.common_tags
}

# Diagnostics Lambda
data "archive_file" "diagnostics" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/diagnostics"
  output_path = "${path.module}/diagnostics.zip"
}

resource "aws_lambda_function" "diagnostics" {
  filename         = data.archive_file.diagnostics.output_path
  function_name    = "${var.environment}-auto-heal-diagnostics"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  source_code_hash = data.archive_file.diagnostics.output_base64sha256
  
  layers = [aws_lambda_layer_version.utils.arn]
  
  environment {
    variables = {
      DIAGNOSTICS_TABLE        = aws_dynamodb_table.diagnostics_history.name
      SSM_DIAGNOSTICS_DOCUMENT = aws_ssm_document.diagnostics.name
      EVENT_BUS_NAME           = var.event_bus_name
    }
  }
  
  vpc_config {
    subnet_ids         = var.enable_vpc ? var.subnet_ids : []
    security_group_ids = var.enable_vpc ? var.security_group_ids : []
  }
  
  depends_on = [
    aws_cloudwatch_log_group.diagnostics,
    aws_iam_role_policy_attachment.lambda_execution
  ]
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-diagnostics"
  })
}

resource "aws_cloudwatch_log_group" "diagnostics" {
  name              = "/aws/lambda/${var.environment}-auto-heal-diagnostics"
  retention_in_days = 14
  
  tags = local.common_tags
}

# Auto-Heal Lambda
data "archive_file" "auto_heal" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/auto_heal"
  output_path = "${path.module}/auto_heal.zip"
}

resource "aws_lambda_function" "auto_heal" {
  filename         = data.archive_file.auto_heal.output_path
  function_name    = "${var.environment}-auto-heal"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  source_code_hash = data.archive_file.auto_heal.output_base64sha256
  
  layers = [aws_lambda_layer_version.utils.arn]
  
  environment {
    variables = {
      AUTO_HEAL_TABLE      = aws_dynamodb_table.auto_heal_history.name
      INSTANCE_CONFIG_TABLE = aws_dynamodb_table.instance_config.name
      SSM_REPAIR_DOCUMENT  = aws_ssm_document.restart_services.name
      EVENT_BUS_NAME       = var.event_bus_name
    }
  }
  
  vpc_config {
    subnet_ids         = var.enable_vpc ? var.subnet_ids : []
    security_group_ids = var.enable_vpc ? var.security_group_ids : []
  }
  
  depends_on = [
    aws_cloudwatch_log_group.auto_heal,
    aws_iam_role_policy_attachment.lambda_execution
  ]
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal"
  })
}

resource "aws_cloudwatch_log_group" "auto_heal" {
  name              = "/aws/lambda/${var.environment}-auto-heal"
  retention_in_days = 14
  
  tags = local.common_tags
}

# Verify Lambda
data "archive_file" "verify" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/verify"
  output_path = "${path.module}/verify.zip"
}

resource "aws_lambda_function" "verify" {
  filename         = data.archive_file.verify.output_path
  function_name    = "${var.environment}-auto-heal-verify"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  source_code_hash = data.archive_file.verify.output_base64sha256
  
  layers = [aws_lambda_layer_version.utils.arn]
  
  environment {
    variables = {
      VERIFICATION_TABLE   = aws_dynamodb_table.verification_history.name
      SSM_VERIFY_DOCUMENT  = aws_ssm_document.verify_health.name
      HEALTH_CHECK_ENDPOINT = var.health_check_endpoint
      HEALTH_CHECK_PORT     = var.health_check_port
      HEALTH_CHECK_TIMEOUT  = "300"
      SNS_TOPIC_ARN         = aws_sns_topic.notifications.arn
    }
  }
  
  vpc_config {
    subnet_ids         = var.enable_vpc ? var.subnet_ids : []
    security_group_ids = var.enable_vpc ? var.security_group_ids : []
  }
  
  depends_on = [
    aws_cloudwatch_log_group.verify,
    aws_iam_role_policy_attachment.lambda_execution
  ]
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-verify"
  })
}

resource "aws_cloudwatch_log_group" "verify" {
  name              = "/aws/lambda/${var.environment}-auto-heal-verify"
  retention_in_days = 14
  
  tags = local.common_tags
}

# Slack Notifier Lambda (if webhook URL provided)
data "archive_file" "slack_notifier" {
  count       = var.slack_webhook_url != "" ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/slack_notifier"
  output_path = "${path.module}/slack_notifier.zip"
}

resource "aws_lambda_function" "slack_notifier" {
  count            = var.slack_webhook_url != "" ? 1 : 0
  filename         = data.archive_file.slack_notifier[0].output_path
  function_name    = "${var.environment}-auto-heal-slack-notifier"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.slack_notifier[0].output_base64sha256
  
  # Slack notifier doesn't need utils layer - uses built-in logging
  # layers = [aws_lambda_layer_version.utils.arn]
  
  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      SLACK_CHANNEL     = var.slack_channel
      SLACK_USERNAME    = var.slack_username
    }
  }
  
  depends_on = [
    aws_cloudwatch_log_group.slack_notifier,
    aws_iam_role_policy_attachment.lambda_execution
  ]
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-slack-notifier"
  })
}

resource "aws_cloudwatch_log_group" "slack_notifier" {
  count             = var.slack_webhook_url != "" ? 1 : 0
  name              = "/aws/lambda/${var.environment}-auto-heal-slack-notifier"
  retention_in_days = 14
  
  tags = local.common_tags
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "target_monitor_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.target_monitor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.target_monitor_schedule.arn
}

resource "aws_lambda_permission" "diagnostics_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.diagnostics.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.diagnostics_trigger.arn
}

resource "aws_lambda_permission" "auto_heal_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auto_heal.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.auto_heal_trigger.arn
}

resource "aws_lambda_permission" "verify_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verify.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.verification_trigger.arn
}

# Lambda permission for SNS to invoke Slack notifier
resource "aws_lambda_permission" "slack_notifier_sns" {
  count         = var.slack_webhook_url != "" ? 1 : 0
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_notifier[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.notifications.arn
}

