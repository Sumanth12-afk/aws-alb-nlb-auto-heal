# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_execution" {
  name = "${var.environment}-auto-heal-lambda-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM Policy for Lambda execution
resource "aws_iam_role_policy" "lambda_execution" {
  name = "${var.environment}-auto-heal-lambda-execution-policy"
  role = aws_iam_role.lambda_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeTargetHealth",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:RegisterTargets",
          "elasticloadbalancing:DeregisterTargets",
          "elbv2:DescribeTargetHealth",
          "elbv2:DescribeTargetGroups",
          "elbv2:RegisterTargets",
          "elbv2:DeregisterTargets"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:TerminateInstances",
          "ec2:DescribeNetworkInterfaces"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation",
          "ssm:StartAutomationExecution",
          "ssm:DescribeAutomationExecutions",
          "ssm:GetAutomationExecution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand"
        ]
        Resource = "arn:aws:ssm:*:*:document/AWS-RunShellScript"
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DescribeAlarms"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.target_health_events.arn,
          "${aws_dynamodb_table.target_health_events.arn}/index/*",
          aws_dynamodb_table.diagnostics_history.arn,
          "${aws_dynamodb_table.diagnostics_history.arn}/index/*",
          aws_dynamodb_table.auto_heal_history.arn,
          "${aws_dynamodb_table.auto_heal_history.arn}/index/*",
          aws_dynamodb_table.instance_config.arn,
          aws_dynamodb_table.verification_history.arn,
          "${aws_dynamodb_table.verification_history.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = var.event_bus_name == "default" ? "*" : "arn:aws:events:${var.aws_region}:*:event-bus/${var.event_bus_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.notifications.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  count      = var.enable_vpc ? 1 : 0
}

# IAM Role for SSM Automation (used by SSM documents)
resource "aws_iam_role" "ssm_automation" {
  name = "${var.environment}-auto-heal-ssm-automation"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ssm.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy" "ssm_automation" {
  name = "${var.environment}-auto-heal-ssm-automation-policy"
  role = aws_iam_role.ssm_automation.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand"
        ]
        Resource = "arn:aws:ssm:*:*:document/AWS-RunShellScript"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus"
        ]
        Resource = "*"
      }
    ]
  })
}

