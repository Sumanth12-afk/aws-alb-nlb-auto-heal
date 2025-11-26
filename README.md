# Dynamic Auto-Heal for Load Balancers (ALB/NLB)

A production-grade, event-driven, serverless automation system that continuously monitors ALB/NLB target health, detects degraded or unhealthy EC2 instances, runs automated diagnostics, performs intelligent healing or replacement actions via Auto Scaling Groups, verifies new instances before registration, and notifies engineering teams with complete incident summaries.

## Features

- **Real-Time Target Health Monitoring**: Continuously tracks ALB/NLB target group health states, response times, HTTP error rates, and flapping targets
- **Automated Diagnostics**: SSM-driven diagnostics engine that classifies failures (Application, Resource Bottleneck, Agent Failure, OS-level, Network, Disk Corruption)
- **Intelligent Auto-Heal Engine**: Supports service-level repair, instance repair, and full instance replacement via Auto Scaling Groups
- **Pre-Registration Verification**: Verifies instance health before re-registering to target groups
- **Comprehensive Notifications**: SNS, Slack, and Microsoft Teams integration with detailed incident summaries
- **State Management**: DynamoDB-backed event history and configuration management

## Architecture

The system is fully serverless and event-driven:

1. **Target Monitor** (Lambda) - Monitors target health on a schedule and via CloudWatch alarms
2. **Diagnostics** (Lambda) - Runs SSM commands to diagnose issues
3. **Auto-Heal** (Lambda) - Performs repair or replacement actions
4. **Verify** (Lambda) - Verifies instance health before re-registration
5. **EventBridge** - Routes events between components
6. **DynamoDB** - Stores health events, diagnostics, and auto-heal history
7. **SSM Automation** - Executes diagnostic and repair commands

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0
- Python 3.12 (for local testing)
- AWS account with permissions to create:
  - Lambda functions
  - DynamoDB tables
  - EventBridge rules
  - SSM documents
  - IAM roles and policies
  - SNS topics

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to project directory
cd "Dynamic Auto-Heal for Load Balancers"

# Edit Terraform variables
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars  # If example exists
# Or create terraform.tfvars manually
```

### 2. Configure terraform.tfvars

```hcl
aws_region = "us-east-1"
environment = "prod"
target_group_arns = [
  "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890123456"
]
monitoring_interval_minutes = 5
health_check_endpoint = "/health"
health_check_port = "80"
```

### 3. Deploy

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Plan deployment
./scripts/deploy.sh prod plan

# Apply deployment
./scripts/deploy.sh prod apply
```

### 4. Configure Notifications

After deployment, configure SNS topic subscriptions:

```bash
# Get SNS topic ARN from Terraform output
terraform output sns_topic_arn

# Subscribe email
aws sns subscribe \
  --topic-arn <topic-arn> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Project Structure

```
/
├─ src/
│  ├─ lambda/
│  │  ├─ target_monitor/     # Health monitoring Lambda
│  │  ├─ diagnostics/        # SSM diagnostics Lambda
│  │  ├─ auto_heal/          # Repair/replacement Lambda
│  │  ├─ verify/              # Verification Lambda
│  │  └─ utils/               # Shared utilities
│  ├─ ssm/
│  │  ├─ diagnostics.yml     # SSM diagnostics document
│  │  ├─ restart_services.yml # SSM repair document
│  │  └─ verify_health.yml    # SSM verification document
│  └─ decision_engine/
│     ├─ diagnosis_rules.json # Classification rules
│     ├─ repair_priority.py   # Priority calculation
│     └─ decision_model.py    # Decision logic
├─ infra/
│  └─ terraform/              # Terraform infrastructure
├─ scripts/
│  ├─ deploy.sh               # Deployment script
│  ├─ teardown.sh             # Teardown script
│  └─ local_debug.sh          # Local testing script
└─ config/
   ├─ policies/               # Instance policies
   └─ thresholds/             # Threshold configurations
```

## Configuration

### Target Groups

Configure target groups to monitor in `terraform.tfvars`:

```hcl
target_group_arns = [
  "arn:aws:elasticloadbalancing:region:account:targetgroup/name/id"
]
```

### Monitoring Interval

Adjust monitoring frequency:

```hcl
monitoring_interval_minutes = 5  # Check every 5 minutes
```

### Instance Configuration

Configure per-instance policies in DynamoDB `InstanceConfig` table:

```json
{
  "InstanceId": "i-1234567890abcdef0",
  "skip_recovery": false,
  "cooldown_minutes": 15,
  "allowed_actions": ["repair", "replace"]
}
```

### Health Check Endpoint

Configure application health check:

```hcl
health_check_endpoint = "/health"
health_check_port = "80"
```

## Usage

### Manual Lambda Invocation

Test individual Lambda functions:

```bash
# Test target monitor
aws lambda invoke \
  --function-name prod-auto-heal-target-monitor \
  --payload '{"target_groups": ["arn:aws:..."]}' \
  response.json

# Test diagnostics
aws lambda invoke \
  --function-name prod-auto-heal-diagnostics \
  --payload '{"instance_id": "i-1234567890abcdef0", "target_group_arn": "arn:aws:..."}' \
  response.json
```

### Local Debugging

Use the local debug script:

```bash
./scripts/local_debug.sh target_monitor test_event.json
```

### Viewing Logs

```bash
# Target Monitor logs
aws logs tail /aws/lambda/prod-auto-heal-target-monitor --follow

# Diagnostics logs
aws logs tail /aws/lambda/prod-auto-heal-diagnostics --follow

# Auto-Heal logs
aws logs tail /aws/lambda/prod-auto-heal --follow

# Verify logs
aws logs tail /aws/lambda/prod-auto-heal-verify --follow
```

## Monitoring and Alerts

### CloudWatch Metrics

The system emits custom metrics for:
- Unhealthy target count
- Healthy target count
- Target response time
- HTTP 5xx error rates
- Auto-heal actions performed

### EventBridge Events

Monitor EventBridge events:

```bash
aws events list-rules --name-prefix prod-auto-heal
```

### DynamoDB Tables

Query health events:

```bash
aws dynamodb query \
  --table-name prod-auto-heal-target-health-events \
  --index-name InstanceId-Timestamp-index \
  --key-condition-expression "InstanceId = :id" \
  --expression-attribute-values '{":id": {"S": "i-1234567890abcdef0"}}'
```

## Troubleshooting

### Lambda Timeout Issues

Increase timeout in `terraform.tfvars`:

```hcl
lambda_timeout = 600  # 10 minutes
```

### SSM Agent Not Available

Ensure instances have SSM agent installed and IAM instance profile with SSM permissions.

### VPC Configuration

If Lambda functions need VPC access:

```hcl
enable_vpc = true
vpc_id = "vpc-12345678"
subnet_ids = ["subnet-12345678", "subnet-87654321"]
security_group_ids = ["sg-12345678"]
```

### Permission Issues

Check IAM role policies. The system requires permissions for:
- ELBv2 (target health, register/deregister)
- EC2 (describe, terminate)
- SSM (send command, automation)
- Auto Scaling (describe, set capacity)
- CloudWatch (metrics, alarms)
- DynamoDB (read/write)
- EventBridge (put events)
- SNS (publish)

## Teardown

To remove all resources:

```bash
./scripts/teardown.sh prod
```

## Development

### Adding New Diagnostic Checks

1. Edit `src/ssm/diagnostics.yml`
2. Update `src/lambda/diagnostics/handler.py` to parse new checks
3. Update `src/decision_engine/diagnosis_rules.json` if needed

### Adding New Repair Actions

1. Edit `src/ssm/restart_services.yml`
2. Update `src/lambda/auto_heal/handler.py` to handle new actions

### Customizing Decision Logic

Edit `src/decision_engine/decision_model.py` and `src/decision_engine/repair_priority.py`

## Security

- All Lambda functions use least-privilege IAM roles
- DynamoDB tables use TTL for automatic cleanup
- SSM documents use IAM roles for execution
- Sensitive values (webhook URLs) should be stored in AWS Secrets Manager or Parameter Store

## Cost Optimization

- DynamoDB uses on-demand billing (PAY_PER_REQUEST)
- Lambda functions use provisioned concurrency only if needed
- CloudWatch logs have 14-day retention
- DynamoDB TTL automatically cleans up old records

## Support

For issues or questions:
1. Check CloudWatch logs for errors
2. Review DynamoDB tables for event history
3. Verify IAM permissions
4. Check SSM agent status on instances

## License

This project is provided as-is for production use.

