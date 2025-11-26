# Custom EventBridge bus (optional)
resource "aws_cloudwatch_event_bus" "auto_heal" {
  count = var.event_bus_name != "default" ? 1 : 0
  name  = var.event_bus_name
  
  tags = local.common_tags
}

# Scheduled rule for target monitoring
resource "aws_cloudwatch_event_rule" "target_monitor_schedule" {
  name                = "${var.environment}-auto-heal-target-monitor-schedule"
  description         = "Scheduled rule for target health monitoring"
  schedule_expression = "rate(${var.monitoring_interval_minutes} minutes)"
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "target_monitor" {
  rule      = aws_cloudwatch_event_rule.target_monitor_schedule.name
  target_id = "TargetMonitorLambda"
  arn       = aws_lambda_function.target_monitor.arn
}

# EventBridge rule for diagnostics trigger
resource "aws_cloudwatch_event_rule" "diagnostics_trigger" {
  name        = "${var.environment}-auto-heal-diagnostics-trigger"
  description = "Trigger diagnostics on target health issues"
  event_bus_name = var.event_bus_name
  
  event_pattern = jsonencode({
    source      = ["auto-heal.target-monitor"]
    detail-type = ["target_health_issue", "unhealthy_target", "degraded_target", "flapping_target"]
  })
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "diagnostics" {
  rule      = aws_cloudwatch_event_rule.diagnostics_trigger.name
  target_id = "DiagnosticsLambda"
  arn       = aws_lambda_function.diagnostics.arn
  event_bus_name = var.event_bus_name
}

# EventBridge rule for auto-heal trigger
resource "aws_cloudwatch_event_rule" "auto_heal_trigger" {
  name        = "${var.environment}-auto-heal-trigger"
  description = "Trigger auto-heal on diagnostics complete"
  event_bus_name = var.event_bus_name
  
  event_pattern = jsonencode({
    source      = ["auto-heal.diagnostics"]
    detail-type = ["Diagnostics Complete"]
  })
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "auto_heal" {
  rule      = aws_cloudwatch_event_rule.auto_heal_trigger.name
  target_id = "AutoHealLambda"
  arn       = aws_lambda_function.auto_heal.arn
  event_bus_name = var.event_bus_name
}

# EventBridge rule for verification trigger
resource "aws_cloudwatch_event_rule" "verification_trigger" {
  name        = "${var.environment}-auto-heal-verification-trigger"
  description = "Trigger verification after auto-heal"
  event_bus_name = var.event_bus_name
  
  event_pattern = jsonencode({
    source      = ["auto-heal.auto-heal"]
    detail-type = ["Auto-Heal Complete"]
  })
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "verify" {
  rule      = aws_cloudwatch_event_rule.verification_trigger.name
  target_id = "VerifyLambda"
  arn       = aws_lambda_function.verify.arn
  event_bus_name = var.event_bus_name
}

