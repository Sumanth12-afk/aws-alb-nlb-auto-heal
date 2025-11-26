# SSM Automation Document: Diagnostics
resource "aws_ssm_document" "diagnostics" {
  name          = "${var.environment}-AutoHeal-Diagnostics"
  document_type = "Automation"
  document_format = "YAML"
  
  content = file("${path.module}/../../src/ssm/diagnostics.yml")
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-AutoHeal-Diagnostics"
  })
}

# SSM Automation Document: Restart Services
resource "aws_ssm_document" "restart_services" {
  name          = "${var.environment}-AutoHeal-RepairServices"
  document_type = "Automation"
  document_format = "YAML"
  
  content = file("${path.module}/../../src/ssm/restart_services.yml")
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-AutoHeal-RepairServices"
  })
}

# SSM Automation Document: Verify Health
resource "aws_ssm_document" "verify_health" {
  name          = "${var.environment}-AutoHeal-VerifyHealth"
  document_type = "Automation"
  document_format = "YAML"
  
  content = file("${path.module}/../../src/ssm/verify_health.yml")
  
  tags = merge(local.common_tags, {
    Name = "${var.environment}-AutoHeal-VerifyHealth"
  })
}

