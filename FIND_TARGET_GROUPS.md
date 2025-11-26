# Finding Your Target Groups

## Option 1: Check Current Region

```powershell
# Check your current AWS region
aws configure get region

# List target groups in current region
aws elbv2 describe-target-groups --query "TargetGroups[*].[TargetGroupName,TargetGroupArn]" --output table
```

## Option 2: Check All Regions

```powershell
# Get all regions
$regions = aws ec2 describe-regions --query "Regions[*].RegionName" --output text

# Check each region for target groups
foreach ($region in $regions) {
    Write-Host "`n=== Checking $region ===" -ForegroundColor Yellow
    aws elbv2 describe-target-groups --region $region --query "TargetGroups[*].[TargetGroupName,TargetGroupArn]" --output table
}
```

## Option 3: Search by Load Balancer

```powershell
# List all load balancers first
aws elbv2 describe-load-balancers --query "LoadBalancers[*].[LoadBalancerName,LoadBalancerArn,DNSName]" --output table

# Then get target groups for a specific load balancer
$lbArn = "arn:aws:elasticloadbalancing:us-east-1:YOUR_ACCOUNT:loadbalancer/app/YOUR_LB_NAME/YOUR_LB_ID"
aws elbv2 describe-target-groups --load-balancer-arn $lbArn --query "TargetGroups[*].[TargetGroupName,TargetGroupArn]" --output table
```

## Option 4: If You Don't Have Target Groups Yet

If you're setting up a new system, you'll need to:
1. Create an Application Load Balancer (ALB) or Network Load Balancer (NLB)
2. Create target groups
3. Register EC2 instances to target groups
4. Then configure this auto-heal system

## Quick Check Command

```powershell
# Check if you have any load balancers at all
aws elbv2 describe-load-balancers --query "LoadBalancers[*].[LoadBalancerName,Type,State.Code]" --output table
```

