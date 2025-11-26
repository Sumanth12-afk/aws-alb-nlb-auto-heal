# Optional: Create ALB and Target Groups for testing
# Set create_sample_alb = true in terraform.tfvars to enable

variable "create_sample_alb" {
  description = "Create a sample ALB with target groups for testing"
  type        = bool
  default     = false
}

variable "sample_vpc_id" {
  description = "VPC ID for sample ALB (required if create_sample_alb = true)"
  type        = string
  default     = ""
}

variable "sample_subnet_ids" {
  description = "Subnet IDs for sample ALB (at least 2 in different AZs)"
  type        = list(string)
  default     = []
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  count       = var.create_sample_alb ? 1 : 0
  name        = "${var.environment}-auto-heal-sample-alb-sg"
  description = "Security group for sample ALB"
  vpc_id      = var.sample_vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-sample-alb-sg"
  })
}

# Application Load Balancer
resource "aws_lb" "sample" {
  count              = var.create_sample_alb ? 1 : 0
  name               = "${var.environment}-auto-heal-sample-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = var.sample_subnet_ids

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-sample-alb"
  })
}

# Target Group
resource "aws_lb_target_group" "sample" {
  count    = var.create_sample_alb ? 1 : 0
  name     = "${var.environment}-auto-heal-sample-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.sample_vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = var.health_check_endpoint
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-sample-tg"
  })
}

# ALB Listener
resource "aws_lb_listener" "sample" {
  count             = var.create_sample_alb ? 1 : 0
  load_balancer_arn = aws_lb.sample[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.sample[0].arn
  }
}

# Output the target group ARN for easy reference
output "sample_target_group_arn" {
  description = "ARN of the sample target group (if created)"
  value       = var.create_sample_alb ? aws_lb_target_group.sample[0].arn : null
}

output "sample_alb_dns_name" {
  description = "DNS name of the sample ALB (if created)"
  value       = var.create_sample_alb ? aws_lb.sample[0].dns_name : null
}

