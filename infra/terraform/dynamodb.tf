resource "aws_dynamodb_table" "target_health_events" {
  name           = "${var.environment}-auto-heal-target-health-events"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "EventId"
  
  attribute {
    name = "EventId"
    type = "S"
  }
  
  attribute {
    name = "InstanceId"
    type = "S"
  }
  
  attribute {
    name = "Timestamp"
    type = "S"
  }
  
  global_secondary_index {
    name            = "InstanceId-Timestamp-index"
    hash_key        = "InstanceId"
    range_key       = "Timestamp"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "TTL"
    enabled        = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-target-health-events"
  })
}

resource "aws_dynamodb_table" "diagnostics_history" {
  name           = "${var.environment}-auto-heal-diagnostics-history"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "DiagnosticId"
  
  attribute {
    name = "DiagnosticId"
    type = "S"
  }
  
  attribute {
    name = "InstanceId"
    type = "S"
  }
  
  attribute {
    name = "Timestamp"
    type = "S"
  }
  
  global_secondary_index {
    name            = "InstanceId-Timestamp-index"
    hash_key        = "InstanceId"
    range_key       = "Timestamp"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "TTL"
    enabled        = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-diagnostics-history"
  })
}

resource "aws_dynamodb_table" "auto_heal_history" {
  name           = "${var.environment}-auto-heal-history"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "ActionId"
  
  attribute {
    name = "ActionId"
    type = "S"
  }
  
  attribute {
    name = "InstanceId"
    type = "S"
  }
  
  attribute {
    name = "Timestamp"
    type = "S"
  }
  
  global_secondary_index {
    name            = "InstanceId-Timestamp-index"
    hash_key        = "InstanceId"
    range_key       = "Timestamp"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "TTL"
    enabled        = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-history"
  })
}

resource "aws_dynamodb_table" "instance_config" {
  name           = "${var.environment}-auto-heal-instance-config"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "InstanceId"
  
  attribute {
    name = "InstanceId"
    type = "S"
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-instance-config"
  })
}

resource "aws_dynamodb_table" "verification_history" {
  name           = "${var.environment}-auto-heal-verification-history"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "VerificationId"
  
  attribute {
    name = "VerificationId"
    type = "S"
  }
  
  attribute {
    name = "InstanceId"
    type = "S"
  }
  
  attribute {
    name = "Timestamp"
    type = "S"
  }
  
  global_secondary_index {
    name            = "InstanceId-Timestamp-index"
    hash_key        = "InstanceId"
    range_key       = "Timestamp"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "TTL"
    enabled        = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-auto-heal-verification-history"
  })
}

