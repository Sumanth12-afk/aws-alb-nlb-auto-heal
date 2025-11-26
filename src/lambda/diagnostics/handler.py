"""SSM-driven diagnostics Lambda handler."""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from utils.aws_clients import (
    get_ssm_client,
    get_ec2_client,
    get_dynamodb_resource
)
from utils.logger import get_logger
from utils.helpers import calculate_diagnostic_score

logger = get_logger(__name__)

# Environment variables
DIAGNOSTICS_TABLE = os.environ.get('DIAGNOSTICS_TABLE', 'DiagnosticsHistory')
SSM_DIAGNOSTICS_DOCUMENT = os.environ.get('SSM_DIAGNOSTICS_DOCUMENT', 'AutoHeal-Diagnostics')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Run SSM diagnostics on unhealthy instances.
    
    Triggered by:
    - EventBridge event from target_monitor
    - Manual invocation
    """
    logger.info("Diagnostics handler started", event=json.dumps(event))
    
    try:
        # Extract instance information from event
        instance_id = _extract_instance_id(event)
        target_group_arn = event.get('target_group_arn', '')
        issue_type = event.get('issue_type', 'unhealthy_target')
        
        if not instance_id:
            logger.error("No instance ID in event")
            return {'statusCode': 400, 'body': 'Missing instance_id'}
        
        logger.info("Running diagnostics", instance_id=instance_id)
        
        # Run SSM diagnostics
        diagnostics_result = _run_ssm_diagnostics(instance_id)
        
        # Classify failure type
        failure_classification = _classify_failure(diagnostics_result)
        
        # Calculate diagnostic score
        diagnostic_score = calculate_diagnostic_score(diagnostics_result)
        
        # Store diagnostics result
        _store_diagnostics(
            instance_id=instance_id,
            target_group_arn=target_group_arn,
            diagnostics=diagnostics_result,
            classification=failure_classification,
            score=diagnostic_score,
            issue_type=issue_type
        )
        
        # Send event to auto-heal if needed
        if diagnostic_score < 70 or failure_classification in ['Application Failure', 'OS-level Failure', 'Disk Corruption']:
            _trigger_auto_heal(instance_id, target_group_arn, diagnostics_result, failure_classification, diagnostic_score)
        
        logger.info("Diagnostics completed",
                   instance_id=instance_id,
                   classification=failure_classification,
                   score=diagnostic_score)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'instance_id': instance_id,
                'classification': failure_classification,
                'diagnostic_score': diagnostic_score,
                'diagnostics': diagnostics_result
            })
        }
    
    except Exception as e:
        logger.error("Diagnostics handler failed", error=str(e), exc_info=True)
        raise


def _extract_instance_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract instance ID from event."""
    # Direct instance_id
    if 'instance_id' in event:
        return event['instance_id']
    
    # From EventBridge detail
    if 'detail' in event:
        detail = event['detail']
        if isinstance(detail, str):
            detail = json.loads(detail)
        return detail.get('instance_id')
    
    return None


def _run_ssm_diagnostics(instance_id: str) -> Dict[str, Any]:
    """Run SSM command to gather diagnostics."""
    ssm = get_ssm_client()
    ec2 = get_ec2_client()
    
    diagnostics = {
        'instance_id': instance_id,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'ssm_available': False,
        'application_failure': False,
        'resource_bottleneck': False,
        'agent_failure': False,
        'os_level_failure': False,
        'network_degradation': False,
        'disk_corruption': False,
        'unknown_state': False
    }
    
    try:
        # Check if SSM agent is available
        response = ssm.describe_instance_information(
            Filters=[
                {
                    'Key': 'InstanceIds',
                    'Values': [instance_id]
                }
            ]
        )
        
        instance_info = response.get('InstanceInformationList', [])
        if not instance_info:
            diagnostics['ssm_available'] = False
            diagnostics['agent_failure'] = True
            diagnostics['unknown_state'] = True
            logger.warning("SSM agent not available", instance_id=instance_id)
            return diagnostics
        
        diagnostics['ssm_available'] = True
        
        # Get instance metadata
        instance_response = ec2.describe_instances(InstanceIds=[instance_id])
        if instance_response.get('Reservations'):
            instance = instance_response['Reservations'][0]['Instances'][0]
            diagnostics['instance_state'] = instance.get('State', {}).get('Name', '')
            diagnostics['instance_type'] = instance.get('InstanceType', '')
        
        # Run SSM command to gather diagnostics
        # This would use the SSM Automation Document
        command_id = _execute_ssm_command(instance_id)
        
        if command_id:
            # Wait for command completion and get results
            diagnostics_data = _get_ssm_command_results(instance_id, command_id)
            diagnostics.update(diagnostics_data)
        
        # Run individual diagnostic checks
        diagnostics.update(_check_service_status(instance_id))
        diagnostics.update(_check_resource_usage(instance_id))
        diagnostics.update(_check_network_stats(instance_id))
        diagnostics.update(_check_logs(instance_id))
    
    except Exception as e:
        logger.error("SSM diagnostics failed", instance_id=instance_id, error=str(e))
        diagnostics['error'] = str(e)
        diagnostics['unknown_state'] = True
    
    return diagnostics


def _execute_ssm_command(instance_id: str) -> Optional[str]:
    """Execute SSM command for diagnostics."""
    ssm = get_ssm_client()
    
    try:
        # Use SSM Automation Document
        response = ssm.start_automation_execution(
            DocumentName=SSM_DIAGNOSTICS_DOCUMENT,
            Parameters={
                'InstanceId': [instance_id]
            }
        )
        return response.get('AutomationExecutionId')
    
    except Exception as e:
        logger.error("Failed to execute SSM command", instance_id=instance_id, error=str(e))
        # Fallback to direct command
        try:
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        'echo "Diagnostics placeholder"'
                    ]
                }
            )
            return response.get('Command', {}).get('CommandId')
        except Exception as e2:
            logger.error("Fallback SSM command failed", error=str(e2))
            return None


def _get_ssm_command_results(instance_id: str, command_id: str) -> Dict[str, Any]:
    """Get results from SSM command execution."""
    ssm = get_ssm_client()
    results = {}
    
    try:
        # Wait for command to complete (simplified - would need polling)
        import time
        time.sleep(2)  # Placeholder
        
        response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        
        status = response.get('Status', '')
        output = response.get('StandardOutputContent', '')
        
        results['ssm_command_status'] = status
        results['ssm_command_output'] = output
        
        # Parse output (would need actual parsing logic)
        if 'error' in output.lower() or status == 'Failed':
            results['application_failure'] = True
    
    except Exception as e:
        logger.error("Failed to get SSM command results", error=str(e))
    
    return results


def _check_service_status(instance_id: str) -> Dict[str, Any]:
    """Check service status via SSM."""
    ssm = get_ssm_client()
    results = {}
    
    try:
        # Check systemd services
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': [
                    'systemctl list-units --type=service --state=failed --no-pager || true',
                    'systemctl is-active docker || echo "docker_inactive"',
                    'systemctl is-active ecs || echo "ecs_inactive"'
                ]
            }
        )
        command_id = response.get('Command', {}).get('CommandId')
        
        # Simplified - would need to wait and parse
        results['service_check_initiated'] = True
    
    except Exception as e:
        logger.error("Service status check failed", error=str(e))
        results['service_check_error'] = str(e)
    
    return results


def _check_resource_usage(instance_id: str) -> Dict[str, Any]:
    """Check CPU, memory, disk usage."""
    ssm = get_ssm_client()
    results = {}
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': [
                    'top -bn1 | grep "Cpu(s)" | awk \'{print $2}\' | cut -d\'%\' -f1',
                    'free -m | awk \'NR==2{printf "%.2f", $3*100/$2}\'',
                    'df -h | awk \'$NF=="/"{print $5}\' | sed \'s/%//\''
                ]
            }
        )
        command_id = response.get('Command', {}).get('CommandId')
        results['resource_check_initiated'] = True
    
    except Exception as e:
        logger.error("Resource usage check failed", error=str(e))
        results['resource_check_error'] = str(e)
    
    return results


def _check_network_stats(instance_id: str) -> Dict[str, Any]:
    """Check network statistics."""
    ssm = get_ssm_client()
    results = {}
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': [
                    'netstat -i | grep -i drop || echo "no_drops"',
                    'ethtool -S eth0 | grep -i error || echo "no_errors"'
                ]
            }
        )
        command_id = response.get('Command', {}).get('CommandId')
        results['network_check_initiated'] = True
    
    except Exception as e:
        logger.error("Network stats check failed", error=str(e))
        results['network_check_error'] = str(e)
    
    return results


def _check_logs(instance_id: str) -> Dict[str, Any]:
    """Check application and system logs."""
    ssm = get_ssm_client()
    results = {}
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': [
                    'tail -n 100 /var/log/syslog | grep -i error || echo "no_errors"',
                    'journalctl -u docker --no-pager -n 50 || echo "no_docker_logs"'
                ]
            }
        )
        command_id = response.get('Command', {}).get('CommandId')
        results['log_check_initiated'] = True
    
    except Exception as e:
        logger.error("Log check failed", error=str(e))
        results['log_check_error'] = str(e)
    
    return results


def _classify_failure(diagnostics: Dict[str, Any]) -> str:
    """Classify failure type based on diagnostics."""
    if diagnostics.get('application_failure'):
        return 'Application Failure'
    elif diagnostics.get('disk_corruption'):
        return 'Disk Corruption'
    elif diagnostics.get('os_level_failure'):
        return 'OS-level Failure'
    elif diagnostics.get('network_degradation'):
        return 'Network Degradation'
    elif diagnostics.get('agent_failure'):
        return 'Agent Failure'
    elif diagnostics.get('resource_bottleneck'):
        return 'Resource Bottleneck'
    elif diagnostics.get('unknown_state'):
        return 'Unknown State'
    else:
        return 'Unknown State'


def _store_diagnostics(
    instance_id: str,
    target_group_arn: str,
    diagnostics: Dict[str, Any],
    classification: str,
    score: float,
    issue_type: str
):
    """Store diagnostics result in DynamoDB."""
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(DIAGNOSTICS_TABLE)
    
    try:
        # Convert float to Decimal for DynamoDB compatibility
        from decimal import Decimal
        
        table.put_item(
            Item={
                'DiagnosticId': f"{instance_id}#{datetime.utcnow().isoformat()}",
                'InstanceId': instance_id,
                'TargetGroupArn': target_group_arn,
                'Classification': classification,
                'DiagnosticScore': Decimal(str(round(score, 2))),
                'Diagnostics': diagnostics,
                'IssueType': issue_type,
                'Timestamp': datetime.utcnow().isoformat() + 'Z',
                'TTL': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
        )
        logger.info("Diagnostics stored", instance_id=instance_id)
    except Exception as e:
        logger.error("Failed to store diagnostics", error=str(e))


def _trigger_auto_heal(
    instance_id: str,
    target_group_arn: str,
    diagnostics: Dict[str, Any],
    classification: str,
    score: float
):
    """Trigger auto-heal process via EventBridge."""
    import boto3
    eventbridge = boto3.client('events')
    
    try:
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'auto-heal.diagnostics',
                    'DetailType': 'Diagnostics Complete',
                    'Detail': json.dumps({
                        'instance_id': instance_id,
                        'target_group_arn': target_group_arn,
                        'classification': classification,
                        'diagnostic_score': score,
                        'diagnostics': diagnostics
                    }),
                    'EventBusName': os.environ.get('EVENT_BUS_NAME', 'default')
                }
            ]
        )
        logger.info("Auto-heal triggered", instance_id=instance_id)
    except Exception as e:
        logger.error("Failed to trigger auto-heal", error=str(e))

