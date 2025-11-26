"""Target health monitoring Lambda handler."""
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from utils.aws_clients import (
    get_elbv2_client,
    get_cloudwatch_client,
    get_dynamodb_resource
)
from utils.logger import get_logger
from utils.helpers import (
    get_target_health_metrics,
    check_flapping,
    parse_target_arn
)

logger = get_logger(__name__)

# Environment variables
TARGET_HEALTH_TABLE = os.environ.get('TARGET_HEALTH_TABLE', 'TargetHealthEvents')
DIAGNOSTICS_TABLE = os.environ.get('DIAGNOSTICS_TABLE', 'DiagnosticsHistory')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Monitor ALB/NLB target health and detect issues.
    
    Triggered by:
    - EventBridge scheduled rule (every 1-5 minutes)
    - CloudWatch alarm state change
    - Manual invocation
    """
    logger.info("Target monitor started", event_type=event.get('source', 'manual'))
    
    try:
        # Get target groups from event or environment
        target_groups = _get_target_groups(event)
        
        if not target_groups:
            logger.warning("No target groups specified")
            return {'statusCode': 200, 'body': 'No target groups to monitor'}
        
        issues_detected = []
        
        for tg_arn in target_groups:
            logger.info("Monitoring target group", target_group_arn=tg_arn)
            issues = _monitor_target_group(tg_arn)
            issues_detected.extend(issues)
        
        # Send events for detected issues
        for issue in issues_detected:
            _send_issue_event(issue)
        
        logger.info("Target monitor completed", issues_detected=len(issues_detected))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'issues_detected': len(issues_detected),
                'issues': issues_detected
            })
        }
    
    except Exception as e:
        logger.error("Target monitor failed", error=str(e), exc_info=True)
        raise


def _get_target_groups(event: Dict[str, Any]) -> List[str]:
    """Extract target group ARNs from event or environment."""
    # From event payload
    if 'target_groups' in event:
        return event['target_groups']
    
    # From environment variable (comma-separated)
    env_tgs = os.environ.get('TARGET_GROUP_ARNS', '')
    if env_tgs:
        return [tg.strip() for tg in env_tgs.split(',')]
    
    # From EventBridge event (CloudWatch alarm)
    if event.get('source') == 'aws.cloudwatch':
        # Extract from alarm dimensions
        alarm_data = event.get('detail', {}).get('configuration', {})
        dimensions = alarm_data.get('dimensions', [])
        for dim in dimensions:
            if dim.get('name') == 'TargetGroup':
                tg_name = dim.get('value')
                # Construct ARN (simplified - would need account/region)
                return [tg_name]
    
    return []


def _monitor_target_group(target_group_arn: str) -> List[Dict[str, Any]]:
    """Monitor a single target group for health issues."""
    elbv2 = get_elbv2_client()
    issues = []
    
    try:
        # Get target health descriptions
        response = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
        targets = response.get('TargetHealthDescriptions', [])
        
        logger.info("Targets in group", 
                   target_group=target_group_arn,
                   total_targets=len(targets))
        
        for target in targets:
            target_info = target.get('Target', {})
            health = target.get('TargetHealth', {})
            instance_id = target_info.get('Id')
            state = health.get('State', '')
            reason = health.get('Reason', '')
            description = health.get('Description', '')
            
            # Record health state change
            _record_health_event(target_group_arn, instance_id, state, reason, description)
            
            # Check for issues
            if state == 'unhealthy':
                issue = {
                    'target_group_arn': target_group_arn,
                    'instance_id': instance_id,
                    'state': state,
                    'reason': reason,
                    'description': description,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'issue_type': 'unhealthy_target'
                }
                issues.append(issue)
            
            # Check for unused state (target not in use due to AZ/subnet issues)
            elif state == 'unused' and 'NotInUse' in reason:
                issue = {
                    'target_group_arn': target_group_arn,
                    'instance_id': instance_id,
                    'state': state,
                    'reason': reason,
                    'description': description,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'issue_type': 'unused_target'
                }
                issues.append(issue)
            
            # Check for degraded state
            elif state == 'draining' or 'degraded' in reason.lower():
                issue = {
                    'target_group_arn': target_group_arn,
                    'instance_id': instance_id,
                    'state': state,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'issue_type': 'degraded_target'
                }
                issues.append(issue)
            
            # Check for flapping
            if _check_target_flapping(target_group_arn, instance_id):
                issue = {
                    'target_group_arn': target_group_arn,
                    'instance_id': instance_id,
                    'state': state,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'issue_type': 'flapping_target'
                }
                issues.append(issue)
        
        # Check aggregate metrics
        aggregate_issues = _check_aggregate_metrics(target_group_arn, targets)
        issues.extend(aggregate_issues)
    
    except Exception as e:
        logger.error("Failed to monitor target group",
                    target_group=target_group_arn,
                    error=str(e))
    
    return issues


def _record_health_event(
    target_group_arn: str,
    instance_id: str,
    state: str,
    reason: str,
    description: str
):
    """Record target health event to DynamoDB."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TARGET_HEALTH_TABLE)
    
    try:
        table.put_item(
            Item={
                'EventId': f"{target_group_arn}#{instance_id}#{datetime.utcnow().isoformat()}",
                'TargetGroupArn': target_group_arn,
                'InstanceId': instance_id,
                'State': state,
                'Reason': reason,
                'Description': description,
                'Timestamp': datetime.utcnow().isoformat() + 'Z',
                'TTL': int((datetime.utcnow() + timedelta(days=30)).timestamp())
            }
        )
    except Exception as e:
        logger.error("Failed to record health event", error=str(e))


def _check_target_flapping(target_group_arn: str, instance_id: str) -> bool:
    """Check if target is flapping."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(TARGET_HEALTH_TABLE)
    
    try:
        # Get recent health events for this target
        response = table.query(
            IndexName='InstanceId-Timestamp-index',  # GSI
            KeyConditionExpression='InstanceId = :instance_id',
            FilterExpression='TargetGroupArn = :tg_arn',
            ExpressionAttributeValues={
                ':instance_id': instance_id,
                ':tg_arn': target_group_arn
            },
            ScanIndexForward=False,
            Limit=10
        )
        
        health_history = response.get('Items', [])
        if len(health_history) < 6:
            return False
        
        # Check for state changes
        states = [item.get('State') for item in health_history]
        changes = sum(1 for i in range(1, len(states)) if states[i] != states[i-1])
        
        return changes >= 3
    
    except Exception as e:
        logger.debug("Flapping check failed", error=str(e))
        return False


def _check_aggregate_metrics(
    target_group_arn: str,
    targets: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Check aggregate CloudWatch metrics for issues."""
    issues = []
    cw = get_cloudwatch_client()
    
    try:
        # Get unhealthy host count
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        response = cw.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName='UnHealthyHostCount',
            Dimensions=[
                {'Name': 'TargetGroup', 'Value': target_group_arn.split('/')[-1]}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Maximum']
        )
        
        datapoints = response.get('Datapoints', [])
        if datapoints:
            max_unhealthy = max(dp.get('Maximum', 0) for dp in datapoints)
            total_targets = len(targets)
            
            if max_unhealthy > 0:
                unhealthy_percentage = (max_unhealthy / total_targets) * 100
                
                if unhealthy_percentage > 50:
                    issues.append({
                        'target_group_arn': target_group_arn,
                        'issue_type': 'high_unhealthy_percentage',
                        'unhealthy_count': max_unhealthy,
                        'total_targets': total_targets,
                        'percentage': unhealthy_percentage,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })
    
    except Exception as e:
        logger.error("Aggregate metrics check failed", error=str(e))
    
    return issues


def _send_issue_event(issue: Dict[str, Any]):
    """Send issue event to EventBridge for processing."""
    import boto3
    eventbridge = boto3.client('events')
    
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'auto-heal.target-monitor',
                    'DetailType': issue.get('issue_type', 'target_health_issue'),
                    'Detail': json.dumps(issue),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
        logger.info("Issue event sent", issue_type=issue.get('issue_type'))
    except Exception as e:
        logger.error("Failed to send issue event", error=str(e))

