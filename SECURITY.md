# Security Documentation - Dynamic Auto-Heal for Load Balancers

## Security Overview

The Dynamic Auto-Heal system is designed with security best practices in mind, following the principle of least privilege and implementing multiple layers of security controls.

## IAM Security

### Least Privilege Principle

All IAM roles and policies follow the principle of least privilege:

#### Lambda Execution Role (`prod-auto-heal-lambda-execution`)

**Permissions:**
- **CloudWatch Logs**: Create log groups, streams, and put log events
- **ELB/ALB**: Describe target health, describe target groups, register/deregister targets
- **EC2**: Describe instances, describe instance status, terminate instances, describe network interfaces
- **SSM**: Send commands, get command invocations, describe instance information, start automation executions
- **Auto Scaling**: Describe ASGs, describe ASG instances, set desired capacity, terminate instances in ASG
- **CloudWatch**: Get metric statistics, put metric alarms, describe alarms
- **DynamoDB**: PutItem, GetItem, UpdateItem, Query, Scan (on specific tables only)
- **EventBridge**: PutEvents
- **SNS**: Publish (to specific topic only)

**Resource Restrictions:**
- DynamoDB permissions are scoped to specific table ARNs
- SNS publish is limited to the specific notification topic ARN
- No wildcard permissions on sensitive resources

#### SSM Automation Role (`prod-auto-heal-ssm-automation`)

**Permissions:**
- **SSM**: Send commands, get command invocations, describe instance information
- **EC2**: Describe instances, describe instance status

**Resource Restrictions:**
- SSM commands limited to `AWS-RunShellScript` document
- Read-only EC2 permissions

### IAM Best Practices

1. **No Wildcard Actions**: All permissions are explicitly defined
2. **Resource-Level Permissions**: Where possible, permissions are scoped to specific resources
3. **Separate Roles**: Different roles for different purposes (Lambda execution vs SSM automation)
4. **No PassRole**: Lambda functions cannot assume other roles
5. **No Administrative Permissions**: No full access to any AWS service

## Network Security

### VPC Configuration

- Lambda functions can be deployed in VPC if required (currently using default VPC)
- Security groups restrict inbound/outbound traffic
- Private subnets recommended for production workloads

### ALB Security Group

The sample ALB security group (if created) includes:
- **Inbound**: HTTP (80) and HTTPS (443) from 0.0.0.0/0 (configurable)
- **Outbound**: All traffic allowed

**Production Recommendations:**
- Restrict inbound rules to specific IP ranges or VPC CIDR
- Use HTTPS only (port 443)
- Implement WAF rules for additional protection

## Data Security

### DynamoDB

- **Encryption**: DynamoDB tables use AWS-managed encryption at rest
- **Access Control**: Tables are only accessible by the Lambda execution role
- **TTL**: Automatic cleanup of old records via TTL attributes
- **No PII**: System does not store personally identifiable information

### Secrets Management

- **Slack Webhook URL**: Stored as Lambda environment variable (consider using AWS Secrets Manager for production)
- **No Hardcoded Credentials**: All credentials are externalized
- **Environment Variables**: Sensitive data passed via environment variables, not in code

## Application Security

### Lambda Security

1. **Code Isolation**: Each Lambda function is isolated
2. **No External Dependencies**: Minimal external dependencies
3. **Input Validation**: All inputs are validated before processing
4. **Error Handling**: Errors are logged but don't expose sensitive information
5. **Timeout Limits**: Functions have appropriate timeout limits to prevent resource exhaustion

### SSM Security

- **Document Permissions**: SSM documents are scoped to specific IAM roles
- **Command Execution**: Only predefined commands can be executed
- **No Interactive Access**: All commands are non-interactive
- **Audit Trail**: All SSM commands are logged in CloudTrail

## Monitoring and Auditing

### CloudWatch Logs

- All Lambda function executions are logged
- Logs include execution context, errors, and performance metrics
- Log retention: 7 days (configurable)

### CloudTrail

- All API calls are logged in CloudTrail
- Includes IAM role assumptions, Lambda invocations, SSM commands
- Enables security auditing and compliance

### EventBridge

- All events are logged
- Event history available for troubleshooting
- No sensitive data in event payloads

## Compliance Considerations

### Data Privacy

- **No PII Storage**: System does not collect or store personally identifiable information
- **Data Retention**: TTL policies ensure automatic data cleanup
- **Data Encryption**: All data encrypted at rest and in transit

### Audit Requirements

- **CloudTrail**: All API calls logged
- **CloudWatch Logs**: Application logs available
- **DynamoDB**: All operations logged
- **EventBridge**: Event history maintained

## Security Best Practices

### Deployment

1. **Use Secrets Manager**: Store sensitive values in AWS Secrets Manager instead of environment variables
2. **Enable VPC**: Deploy Lambda functions in VPC for additional network isolation
3. **Enable Encryption**: Ensure all data is encrypted at rest and in transit
4. **Regular Updates**: Keep Lambda runtime and dependencies updated
5. **Code Review**: Review all code changes before deployment

### Runtime

1. **Monitor Logs**: Regularly review CloudWatch logs for anomalies
2. **Alert on Errors**: Set up CloudWatch alarms for Lambda errors
3. **Review IAM Policies**: Periodically review and audit IAM permissions
4. **Update SSM Documents**: Keep SSM documents updated with security patches
5. **Rotate Credentials**: Regularly rotate Slack webhook URLs and other credentials

### Access Control

1. **Terraform State**: Store Terraform state in encrypted S3 bucket with versioning
2. **IAM Users**: Use IAM roles for Terraform execution, not IAM users
3. **MFA**: Enable MFA for all AWS accounts
4. **Least Privilege**: Regularly audit and reduce IAM permissions

## Security Incident Response

### Detection

- Monitor CloudWatch alarms for unusual activity
- Review CloudTrail logs for unauthorized access
- Check Lambda error rates and execution patterns

### Response

1. **Immediate**: Disable affected Lambda functions if compromise detected
2. **Investigation**: Review CloudTrail and CloudWatch logs
3. **Containment**: Revoke compromised credentials
4. **Recovery**: Redeploy from known good state
5. **Post-Incident**: Document lessons learned and update security controls

## Security Checklist

- [ ] IAM roles follow least privilege principle
- [ ] DynamoDB tables have encryption enabled
- [ ] Lambda environment variables don't contain secrets
- [ ] CloudWatch Logs retention configured
- [ ] CloudTrail enabled and monitored
- [ ] Security groups restrict access appropriately
- [ ] SSM documents are reviewed and approved
- [ ] Regular security audits scheduled
- [ ] Incident response plan documented
- [ ] Secrets stored in AWS Secrets Manager (production)

## Known Security Considerations

### Current Limitations

1. **Slack Webhook in Environment Variable**: Consider moving to Secrets Manager
2. **Public ALB**: Sample ALB allows public access (restrict in production)
3. **No VPC Deployment**: Lambda functions not in VPC (add for production)
4. **No WAF**: Web Application Firewall not configured (add for production ALB)

### Future Enhancements

1. Integrate AWS Secrets Manager for sensitive data
2. Deploy Lambda functions in VPC
3. Add WAF rules to ALB
4. Implement AWS Config rules for compliance
5. Add AWS GuardDuty for threat detection
6. Enable AWS Security Hub for centralized security management

## Contact

For security concerns or to report vulnerabilities, please follow your organization's security incident reporting process.

