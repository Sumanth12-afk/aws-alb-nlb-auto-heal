# Dynamic Auto-Heal for Load Balancers - Commands Reference

Quick reference guide for deploying, managing, and testing the Dynamic Auto-Heal system.

## Prerequisites

```powershell
# Ensure AWS CLI is configured
aws configure list

# Ensure Terraform is installed
terraform version

```

## Initial Setup

### 1. Configure Terraform Variables

```powershell
# Copy example variables file
Copy-Item terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values:
# - AWS region
# - Target group ARNs
# - Slack webhook URL (optional)
# - VPC and subnet IDs (if creating sample ALB)
```

### 2. Initialize Terraform

```powershell
terraform init
```

## Deployment Commands

### Deploy Infrastructure

```powershell
# Plan deployment
terraform plan

# Apply deployment
terraform apply

# Auto-approve (skip confirmation)
terraform apply -auto-approve
```

### Destroy Infrastructure

```powershell
# Plan destruction
terraform destroy

# Auto-approve destruction
terraform destroy -auto-approve
```

## Testing Commands

### Test Target Monitor Lambda

```powershell
# Get target group ARN
$tgArn = terraform output -raw sample_target_group_arn

# Create payload file
@{
    source = "manual"
    target_groups = @($tgArn)
} | ConvertTo-Json -Compress | Out-File -FilePath payload.json -Encoding utf8

# Invoke Lambda
aws lambda invoke --function-name prod-auto-heal-target-monitor --cli-binary-format raw-in-base64-out --payload file://payload.json response.json

# View response
Get-Content response.json
```

### Test Slack Notifications

```powershell
# Get SNS topic ARN
$topicArn = terraform output -raw sns_topic_arn

# Send test message
$testMsg = '{"event_type":"unhealthy_target","instance_id":"i-1234567890abcdef0","target_group_arn":"arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/test-tg/1234567890123456","classification":"Application Failure","diagnostic_score":45.5,"action":"repair","timestamp":"' + (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ") + '","message":"Test notification: Unhealthy target detected"}'
aws sns publish --topic-arn $topicArn --subject "Test Alert" --message $testMsg
```

### Check Lambda Logs

```powershell
# Target Monitor logs
aws logs tail /aws/lambda/prod-auto-heal-target-monitor --since 10m

# Diagnostics logs
aws logs tail /aws/lambda/prod-auto-heal-diagnostics --since 10m

# Auto-Heal logs
aws logs tail /aws/lambda/prod-auto-heal --since 10m

# Verify logs
aws logs tail /aws/lambda/prod-auto-heal-verify --since 10m

# Slack Notifier logs
aws logs tail /aws/lambda/prod-auto-heal-slack-notifier --since 10m
```

## Monitoring Commands

### Check DynamoDB Tables

```powershell
# List all tables
aws dynamodb list-tables

# Scan target health events
aws dynamodb scan --table-name prod-auto-heal-target-health-events --limit 5

# Scan diagnostics history
aws dynamodb scan --table-name prod-auto-heal-diagnostics-history --limit 5

# Scan auto-heal history
aws dynamodb scan --table-name prod-auto-heal-history --limit 5
```

### Check EventBridge Rules

```powershell
# List EventBridge rules
aws events list-rules --name-prefix prod-auto-heal

# Describe target monitor schedule
aws events describe-rule --name prod-auto-heal-target-monitor-schedule
```

### Check Lambda Functions

```powershell
# List all Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, 'auto-heal')].FunctionName"

# Get function details
aws lambda get-function --function-name prod-auto-heal-target-monitor
```

## Target Group Management

### Find Target Groups

```powershell
# List all target groups
aws elbv2 describe-target-groups --region us-east-1 --query "TargetGroups[*].[TargetGroupName,TargetGroupArn]" --output table

# Get target group ARNs only
aws elbv2 describe-target-groups --region us-east-1 --query "TargetGroups[*].TargetGroupArn" --output text
```

### Check Target Health

```powershell
# Get target group ARN
$tgArn = terraform output -raw sample_target_group_arn

# Check target health
aws elbv2 describe-target-health --target-group-arn $tgArn
```

### Register/Deregister Targets

```powershell
# Register instance to target group
aws elbv2 register-targets --target-group-arn $tgArn --targets Id=i-1234567890abcdef0

# Deregister instance
aws elbv2 deregister-targets --target-group-arn $tgArn --targets Id=i-1234567890abcdef0
```

## VPC and Network Setup

### Get VPC Information

```powershell
# Get default VPC
$vpcId = aws ec2 describe-vpcs --region us-east-1 --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text
Write-Host "VPC ID: $vpcId"

# Get subnets in VPC
aws ec2 describe-subnets --region us-east-1 --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[*].[SubnetId,AvailabilityZone,CidrBlock]" --output table
```

## Outputs

### Get Terraform Outputs

```powershell
# List all outputs
terraform output

# Get specific output
terraform output -raw sns_topic_arn
terraform output -raw sample_target_group_arn
terraform output -raw sample_alb_dns_name
```

## Troubleshooting

### Check IAM Permissions

```powershell
# Test Lambda execution role
aws iam get-role --role-name prod-auto-heal-lambda-execution

# List role policies
aws iam list-role-policies --role-name prod-auto-heal-lambda-execution
```

### Verify SSM Documents

```powershell
# List SSM documents
aws ssm list-documents --document-filter-list key=Name,value=prod-AutoHeal

# Get document details
aws ssm describe-document --name prod-AutoHeal-Diagnostics
```

### Check EventBridge Targets

```powershell
# List targets for a rule
aws events list-targets-by-rule --rule prod-auto-heal-target-monitor-schedule
```

## Cleanup

### Remove All Resources

```powershell
# Destroy all infrastructure
terraform destroy -auto-approve

# Verify resources are deleted
aws lambda list-functions --query "Functions[?contains(FunctionName, 'auto-heal')].FunctionName"
aws dynamodb list-tables --query "TableNames[?contains(@, 'auto-heal')]"
```

## Quick Health Check

```powershell
# Run all health checks
Write-Host "=== Lambda Functions ==="
aws lambda list-functions --query "Functions[?contains(FunctionName, 'auto-heal')].FunctionName"

Write-Host "`n=== DynamoDB Tables ==="
aws dynamodb list-tables --query "TableNames[?contains(@, 'auto-heal')]"

Write-Host "`n=== EventBridge Rules ==="
aws events list-rules --name-prefix prod-auto-heal --query "Rules[*].Name"

Write-Host "`n=== SNS Topic ==="
terraform output -raw sns_topic_arn
```

