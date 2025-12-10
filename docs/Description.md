AWS ALB/NLB Auto-Heal System

## What the Solution Does

This solution continuously monitors target health behind Application Load Balancers (ALB) and Network Load Balancers (NLB) and automatically repairs unhealthy instances.

## Why It Exists

Unhealthy load-balancer targets cause:

- Downtime
- Slow responses
- Failed customer requests

Most teams detect these late and fix them manually.

This automation ensures that load balancers always serve traffic from healthy targets.

## Use Cases

- Web applications behind ALB/NLB
- Microservices requiring strict uptime
- Auto-scaling groups with unpredictable failures
- Multi-AZ distributed deployments

## High-Level Architecture

- ALB/NLB health checks to CloudWatch
- EventBridge triggers detection workflow
- Lambda performs diagnosis
- Instance auto-heal action (restart, detach/attach, replace)
- Slack/SNS notifications

## Features

- Continuous LB target monitoring
- Automated repair actions
- Intelligent target rotation
- Zero-downtime healing
- Alerts for persistent failures

## Benefits

- Higher uptime for web applications
- Faster recovery from backend failures
- Reduced manual debugging
- More stable traffic distribution

## Business Problem It Solves

Load balancer issues often go unnoticed until severe customer impact occurs. This system detects problems instantly and corrects them with minimal disruption.

## How It Works (Non-Code Workflow)

LB health checks identify unhealthy targets. EventBridge notifies the healing workflow. Lambda verifies the failure type. The instance is repaired or replaced. Load balancer automatically re-registers the healthy target.

## Additional Explanation

This system integrates perfectly with Auto Scaling Groups and improves resilience for any workload using AWS load balancers.
