# Quick Start Commands

## Prerequisites Check

```powershell
# Check AWS CLI
aws --version

# Check Terraform
terraform version

# Check Python
python --version
```

## Initial Setup

```powershell
# Navigate to project directory
cd "C:\Users\nalla\OneDrive\Desktop\Projects of BYS\Dynamic Auto-Heal for Load Balancers"

# Verify AWS credentials
aws sts get-caller-identity

# Initialize Terraform
cd infra\terraform
terraform init
```

## Configuration

```powershell
# Create terraform.tfvars file
@"
aws_region = "us-east-1"
environment = "prod"
target_group_arns = [
  "arn:aws:elasticloadbalancing:us-east-1:YOUR_ACCOUNT:targetgroup/YOUR_TG_NAME/YOUR_TG_ID"
]
monitoring_interval_minutes = 5
health_check_endpoint = "/health"
health_check_port = "80"
lambda_timeout = 300
lambda_memory_size = 512
enable_vpc = false
event_bus_name = "default"
"@ | Out-File -FilePath terraform.tfvars -Encoding utf8

# Edit terraform.tfvars with your actual values
notepad terraform.tfvars
```

## Deployment

```powershell
# Plan deployment (review changes)
terraform plan -var="environment=prod" -out=tfplan

# Apply deployment (creates all resources)
terraform apply -var="environment=prod" -auto-approve

# OR use the deploy script (Linux/Mac/Git Bash)
bash scripts/deploy.sh prod apply
```

## Verify Deployment

```powershell
# List deployed Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, 'auto-heal')].FunctionName"

# Check DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'auto-heal')]"

# View EventBridge rules
aws events list-rules --name-prefix prod-auto-heal

# Get SNS topic ARN
terraform output sns_topic_arn
```

## Configure Notifications

```powershell
# Subscribe email to SNS topic
$topicArn = terraform output -raw sns_topic_arn
aws sns subscribe --topic-arn $topicArn --protocol email --notification-endpoint your-email@example.com

# Check subscription (confirm via email)
aws sns list-subscriptions-by-topic --topic-arn $topicArn
```

## Test the System

### Test Target Monitor

```powershell
# Invoke target monitor manually
$functionName = "prod-auto-heal-target-monitor"
$payload = @{
    source = "manual"
    target_groups = @("arn:aws:elasticloadbalancing:us-east-1:YOUR_ACCOUNT:targetgroup/YOUR_TG_NAME/YOUR_TG_ID")
} | ConvertTo-Json

aws lambda invoke --function-name $functionName --payload $payload response.json
Get-Content response.json | ConvertFrom-Json
```

### Test Diagnostics

```powershell
# Invoke diagnostics manually
$functionName = "prod-auto-heal-diagnostics"
$payload = @{
    instance_id = "i-1234567890abcdef0"
    target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:YOUR_ACCOUNT:targetgroup/YOUR_TG_NAME/YOUR_TG_ID"
    issue_type = "unhealthy_target"
} | ConvertTo-Json

aws lambda invoke --function-name $functionName --payload $payload response.json
Get-Content response.json | ConvertFrom-Json
```

## Monitor Logs

```powershell
# Tail target monitor logs
aws logs tail /aws/lambda/prod-auto-heal-target-monitor --follow

# Tail diagnostics logs
aws logs tail /aws/lambda/prod-auto-heal-diagnostics --follow

# Tail auto-heal logs
aws logs tail /aws/lambda/prod-auto-heal --follow

# Tail verify logs
aws logs tail /aws/lambda/prod-auto-heal-verify --follow
```

## Query DynamoDB

```powershell
# Query target health events
aws dynamodb query `
    --table-name prod-auto-heal-target-health-events `
    --index-name InstanceId-Timestamp-index `
    --key-condition-expression "InstanceId = :id" `
    --expression-attribute-values '{":id": {"S": "i-1234567890abcdef0"}}'

# Scan diagnostics history
aws dynamodb scan --table-name prod-auto-heal-diagnostics-history --limit 5

# Scan auto-heal history
aws dynamodb scan --table-name prod-auto-heal-auto-heal-history --limit 5
```

## Local Testing (Python)

```powershell
# Set up Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install boto3

# Test locally (requires AWS credentials configured)
cd ..
python -c "import sys; sys.path.insert(0, 'src/lambda'); from target_monitor.handler import lambda_handler; print(lambda_handler({'source': 'manual'}, None))"
```

## Troubleshooting

```powershell
# Check Lambda function configuration
aws lambda get-function --function-name prod-auto-heal-target-monitor

# Check Lambda errors
aws logs filter-log-events `
    --log-group-name /aws/lambda/prod-auto-heal-target-monitor `
    --filter-pattern "ERROR" `
    --max-items 10

# Test SSM agent on instance
aws ssm describe-instance-information --filters "Key=InstanceIds,Values=i-1234567890abcdef0"

# Check EventBridge events
aws events list-rules --name-prefix prod-auto-heal
aws events describe-rule --name prod-auto-heal-target-monitor-schedule
```

## Teardown

```powershell
# Destroy all resources
terraform destroy -var="environment=prod" -auto-approve

# OR use teardown script (Linux/Mac/Git Bash)
bash scripts/teardown.sh prod
```

## Common Commands Reference

```powershell
# Get all outputs
terraform output

# Refresh state
terraform refresh

# Validate Terraform
terraform validate

# Format Terraform files
terraform fmt -recursive

# Check Lambda function status
aws lambda get-function-configuration --function-name prod-auto-heal-target-monitor

# Update Lambda environment variables
aws lambda update-function-configuration `
    --function-name prod-auto-heal-target-monitor `
    --environment "Variables={TARGET_GROUP_ARNS=arn:aws:...}"

# Manually trigger EventBridge rule
aws events put-events --entries '[{"Source":"manual","DetailType":"Test","Detail":"{\"test\":\"data\"}"}]'
```

