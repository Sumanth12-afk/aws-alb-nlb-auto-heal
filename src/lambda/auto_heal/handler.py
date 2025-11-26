"""Auto-heal Lambda handler for repair and replacement."""
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.aws_clients import (
    get_elbv2_client,
    get_ec2_client,
    get_autoscaling_client,
    get_ssm_client,
    get_dynamodb_resource
)
from utils.logger import get_logger
from utils.helpers import should_replace_instance

logger = get_logger(__name__)

# Environment variables
AUTO_HEAL_TABLE = os.environ.get('AUTO_HEAL_TABLE', 'AutoHealHistory')
INSTANCE_CONFIG_TABLE = os.environ.get('INSTANCE_CONFIG_TABLE', 'InstanceConfig')
SSM_REPAIR_DOCUMENT = os.environ.get('SSM_REPAIR_DOCUMENT', 'AutoHeal-RepairServices')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Auto-heal handler for repair and replacement.
    
    Triggered by:
    - EventBridge event from diagnostics
    - Manual invocation
    """
    logger.info("Auto-heal handler started", event=json.dumps(event))
    
    try:
        # Extract information from event
        instance_id = _extract_instance_id(event)
        target_group_arn = event.get('target_group_arn', '')
        diagnostic_score = event.get('diagnostic_score', 100.0)
        classification = event.get('classification', 'Unknown State')
        
        if not instance_id:
            logger.error("No instance ID in event")
            return {'statusCode': 400, 'body': 'Missing instance_id'}
        
        # Check instance configuration
        instance_config = _get_instance_config(instance_id)
        
        if instance_config.get('skip_recovery', False):
            logger.info("Recovery skipped for instance", instance_id=instance_id)
            return {'statusCode': 200, 'body': 'Recovery skipped per configuration'}
        
        # Check cooldown period
        if _is_in_cooldown(instance_id, instance_config):
            logger.info("Instance in cooldown period", instance_id=instance_id)
            return {'statusCode': 200, 'body': 'Instance in cooldown period'}
        
        # Get repair attempts
        repair_attempts = _get_repair_attempts(instance_id)
        
        # Decide: repair or replace
        should_replace = should_replace_instance(diagnostic_score, repair_attempts)
        
        if should_replace:
            logger.info("Replacing instance", instance_id=instance_id)
            result = _replace_instance(instance_id, target_group_arn, classification, diagnostic_score)
        else:
            logger.info("Attempting repair", instance_id=instance_id)
            result = _repair_instance(instance_id, target_group_arn, classification, diagnostic_score)
        
        # Record auto-heal action
        _record_auto_heal_action(
            instance_id=instance_id,
            target_group_arn=target_group_arn,
            action=result['action'],
            result=result,
            classification=classification,
            diagnostic_score=diagnostic_score
        )
        
        # Trigger verification
        if result.get('success'):
            _trigger_verification(instance_id, target_group_arn, result)
        
        logger.info("Auto-heal completed", instance_id=instance_id, action=result['action'])
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    
    except Exception as e:
        logger.error("Auto-heal handler failed", error=str(e), exc_info=True)
        raise


def _extract_instance_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract instance ID from event."""
    if 'instance_id' in event:
        return event['instance_id']
    
    if 'detail' in event:
        detail = event['detail']
        if isinstance(detail, str):
            detail = json.loads(detail)
        return detail.get('instance_id')
    
    return None


def _get_instance_config(instance_id: str) -> Dict[str, Any]:
    """Get instance configuration from DynamoDB."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(INSTANCE_CONFIG_TABLE)
    
    try:
        response = table.get_item(Key={'InstanceId': instance_id})
        return response.get('Item', {})
    except Exception as e:
        logger.debug("Failed to get instance config", error=str(e))
        return {}


def _is_in_cooldown(instance_id: str, config: Dict[str, Any]) -> bool:
    """Check if instance is in cooldown period."""
    cooldown_minutes = config.get('cooldown_minutes', 15)
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(AUTO_HEAL_TABLE)
    
    try:
        # Get last auto-heal action
        response = table.query(
            IndexName='InstanceId-Timestamp-index',
            KeyConditionExpression='InstanceId = :instance_id',
            ExpressionAttributeValues={':instance_id': instance_id},
            ScanIndexForward=False,
            Limit=1
        )
        
        items = response.get('Items', [])
        if not items:
            return False
        
        last_action_time = datetime.fromisoformat(items[0]['Timestamp'].replace('Z', '+00:00'))
        time_since_last_action = datetime.utcnow().replace(tzinfo=last_action_time.tzinfo) - last_action_time
        
        return time_since_last_action.total_seconds() < (cooldown_minutes * 60)
    
    except Exception as e:
        logger.debug("Cooldown check failed", error=str(e))
        return False


def _get_repair_attempts(instance_id: str) -> int:
    """Get number of repair attempts for instance."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(AUTO_HEAL_TABLE)
    
    try:
        response = table.query(
            IndexName='InstanceId-Timestamp-index',
            KeyConditionExpression='InstanceId = :instance_id',
            FilterExpression='Action = :action',
            ExpressionAttributeValues={
                ':instance_id': instance_id,
                ':action': 'repair'
            },
            ScanIndexForward=False
        )
        
        return len(response.get('Items', []))
    
    except Exception as e:
        logger.debug("Failed to get repair attempts", error=str(e))
        return 0


def _repair_instance(
    instance_id: str,
    target_group_arn: str,
    classification: str,
    diagnostic_score: float
) -> Dict[str, Any]:
    """Attempt to repair instance via SSM."""
    ssm = get_ssm_client()
    elbv2 = get_elbv2_client()
    
    result = {
        'action': 'repair',
        'instance_id': instance_id,
        'success': False,
        'steps': [],
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    try:
        # Step 1: Deregister from target group
        logger.info("Deregistering instance from target group", instance_id=instance_id)
        try:
            elbv2.deregister_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{'Id': instance_id}]
            )
            result['steps'].append({
                'step': 'deregister_target',
                'status': 'success'
            })
        except Exception as e:
            logger.error("Failed to deregister target", error=str(e))
            result['steps'].append({
                'step': 'deregister_target',
                'status': 'failed',
                'error': str(e)
            })
        
        # Step 2: Run SSM repair document
        logger.info("Running SSM repair document", instance_id=instance_id)
        try:
            response = ssm.start_automation_execution(
                DocumentName=SSM_REPAIR_DOCUMENT,
                Parameters={
                    'InstanceId': [instance_id],
                    'Classification': [classification]
                }
            )
            automation_execution_id = response.get('AutomationExecutionId')
            result['steps'].append({
                'step': 'ssm_repair',
                'status': 'initiated',
                'automation_execution_id': automation_execution_id
            })
            
            # Wait for completion (simplified - would need polling)
            result['success'] = True
        
        except Exception as e:
            logger.error("SSM repair failed", error=str(e))
            result['steps'].append({
                'step': 'ssm_repair',
                'status': 'failed',
                'error': str(e)
            })
        
        # Step 3: Re-register to target group (after verification)
        # This will be done by the verify Lambda
        
    except Exception as e:
        logger.error("Repair process failed", error=str(e))
        result['error'] = str(e)
    
    return result


def _replace_instance(
    instance_id: str,
    target_group_arn: str,
    classification: str,
    diagnostic_score: float
) -> Dict[str, Any]:
    """Replace instance via Auto Scaling Group."""
    elbv2 = get_elbv2_client()
    autoscaling = get_autoscaling_client()
    ec2 = get_ec2_client()
    
    result = {
        'action': 'replace',
        'instance_id': instance_id,
        'replacement_instance_id': None,
        'success': False,
        'steps': [],
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    try:
        # Step 1: Get Auto Scaling Group for instance
        asg_name = _get_asg_for_instance(instance_id)
        if not asg_name:
            logger.error("No ASG found for instance", instance_id=instance_id)
            result['error'] = 'No ASG found for instance'
            return result
        
        result['asg_name'] = asg_name
        
        # Step 2: Deregister from target group
        logger.info("Deregistering instance from target group", instance_id=instance_id)
        try:
            elbv2.deregister_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{'Id': instance_id}]
            )
            result['steps'].append({
                'step': 'deregister_target',
                'status': 'success'
            })
        except Exception as e:
            logger.error("Failed to deregister target", error=str(e))
            result['steps'].append({
                'step': 'deregister_target',
                'status': 'failed',
                'error': str(e)
            })
        
        # Step 3: Get current ASG capacity
        asg_response = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )
        asg = asg_response['AutoScalingGroups'][0]
        min_size = asg['MinSize']
        desired_capacity = asg['DesiredCapacity']
        
        # Step 4: Terminate instance (ASG will replace it)
        logger.info("Terminating instance", instance_id=instance_id)
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
            result['steps'].append({
                'step': 'terminate_instance',
                'status': 'success'
            })
        except Exception as e:
            logger.error("Failed to terminate instance", error=str(e))
            result['steps'].append({
                'step': 'terminate_instance',
                'status': 'failed',
                'error': str(e)
            })
            return result
        
        # Step 5: Wait for replacement (simplified - would need polling)
        # In production, this would poll ASG for new instance
        result['steps'].append({
            'step': 'wait_for_replacement',
            'status': 'initiated'
        })
        
        # Step 6: Ensure min capacity maintained
        if desired_capacity <= min_size:
            logger.info("Increasing desired capacity to maintain min", asg_name=asg_name)
            try:
                autoscaling.set_desired_capacity(
                    AutoScalingGroupName=asg_name,
                    DesiredCapacity=desired_capacity + 1,
                    HonorCooldown=False
                )
                result['steps'].append({
                    'step': 'increase_capacity',
                    'status': 'success'
                })
            except Exception as e:
                logger.error("Failed to increase capacity", error=str(e))
        
        result['success'] = True
        
    except Exception as e:
        logger.error("Replace process failed", error=str(e))
        result['error'] = str(e)
    
    return result


def _get_asg_for_instance(instance_id: str) -> Optional[str]:
    """Get Auto Scaling Group name for instance."""
    autoscaling = get_autoscaling_client()
    
    try:
        response = autoscaling.describe_auto_scaling_instances(
            InstanceIds=[instance_id]
        )
        
        instances = response.get('AutoScalingInstances', [])
        if instances:
            return instances[0].get('AutoScalingGroupName')
    
    except Exception as e:
        logger.error("Failed to get ASG for instance", error=str(e))
    
    return None


def _record_auto_heal_action(
    instance_id: str,
    target_group_arn: str,
    action: str,
    result: Dict[str, Any],
    classification: str,
    diagnostic_score: float
):
    """Record auto-heal action to DynamoDB."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(AUTO_HEAL_TABLE)
    
    try:
        # Convert float to Decimal for DynamoDB compatibility
        from decimal import Decimal
        
        table.put_item(
            Item={
                'ActionId': f"{instance_id}#{datetime.utcnow().isoformat()}",
                'InstanceId': instance_id,
                'TargetGroupArn': target_group_arn,
                'Action': action,
                'Result': result,
                'Classification': classification,
                'DiagnosticScore': Decimal(str(round(diagnostic_score, 2))),
                'Timestamp': datetime.utcnow().isoformat() + 'Z',
                'TTL': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
        )
        logger.info("Auto-heal action recorded", instance_id=instance_id, action=action)
    except Exception as e:
        logger.error("Failed to record auto-heal action", error=str(e))


def _trigger_verification(
    instance_id: str,
    target_group_arn: str,
    result: Dict[str, Any]
):
    """Trigger verification process via EventBridge."""
    import boto3
    eventbridge = boto3.client('events')
    
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'auto-heal.auto-heal',
                    'DetailType': 'Auto-Heal Complete',
                    'Detail': json.dumps({
                        'instance_id': instance_id,
                        'target_group_arn': target_group_arn,
                        'action': result.get('action'),
                        'result': result
                    }),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
        logger.info("Verification triggered", instance_id=instance_id)
    except Exception as e:
        logger.error("Failed to trigger verification", error=str(e))

