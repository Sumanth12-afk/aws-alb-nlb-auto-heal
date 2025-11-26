# Getting VPC and Subnet Information

Before creating the sample ALB, you need to get your VPC ID and subnet IDs.

## Get VPC Information

```powershell
# List all VPCs
aws ec2 describe-vpcs --region us-east-1 --query "Vpcs[*].[VpcId,CidrBlock,Tags[?Key=='Name'].Value|[0]]" --output table

# Get default VPC
aws ec2 describe-vpcs --region us-east-1 --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text
```

## Get Subnet Information

```powershell
# List all subnets in a VPC (replace vpc-xxxxx with your VPC ID)
$vpcId = "vpc-12345678"
aws ec2 describe-subnets --region us-east-1 --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[*].[SubnetId,AvailabilityZone,CidrBlock,Tags[?Key=='Name'].Value|[0]]" --output table

# Get public subnets (for internet-facing ALB)
aws ec2 describe-subnets --region us-east-1 --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].[SubnetId,AvailabilityZone]" --output table
```

## Quick Setup

1. Get your VPC ID:
   ```powershell
   $vpcId = aws ec2 describe-vpcs --region us-east-1 --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text
   Write-Host "VPC ID: $vpcId"
   ```

2. Get subnet IDs (need at least 2 in different AZs):
   ```powershell
   $subnets = aws ec2 describe-subnets --region us-east-1 --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text
   Write-Host "Subnet IDs: $subnets"
   ```

3. Update `terraform.tfvars`:
   ```hcl
   create_sample_alb = true
   sample_vpc_id = "vpc-xxxxx"
   sample_subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
   ```

4. Apply:
   ```powershell
   terraform apply
   ```

5. Get the created target group ARN:
   ```powershell
   terraform output sample_target_group_arn
   ```

6. Update `target_group_arns` in terraform.tfvars with the output ARN.

