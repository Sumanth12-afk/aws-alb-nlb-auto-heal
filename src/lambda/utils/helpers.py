"""Helper utilities for Lambda functions."""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .aws_clients import get_cloudwatch_client, get_elbv2_client


def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with optional default."""
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is required")
    return value


def parse_target_arn(target_arn: str) -> Dict[str, str]:
    """Parse target ARN into components."""
    parts = target_arn.split(':')
    return {
        'region': parts[3],
        'account_id': parts[4],
        'target_group': parts[5].split('/')[-1],
        'target_id': parts[6]
    }


def get_target_health_metrics(
    target_group_arn: str,
    instance_id: str,
    minutes: int = 5
) -> Dict[str, Any]:
    """Get CloudWatch metrics for target health."""
    cw = get_cloudwatch_client()
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=minutes)
    
    metrics = {}
    
    # Get UnHealthyHostCount
    try:
        response = cw.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName='UnHealthyHostCount',
            Dimensions=[
                {'Name': 'TargetGroup', 'Value': target_group_arn.split('/')[-1]}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Average', 'Maximum']
        )
        metrics['unhealthy_host_count'] = response.get('Datapoints', [])
    except Exception as e:
        metrics['unhealthy_host_count_error'] = str(e)
    
    # Get HealthyHostCount
    try:
        response = cw.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName='HealthyHostCount',
            Dimensions=[
                {'Name': 'TargetGroup', 'Value': target_group_arn.split('/')[-1]}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Average', 'Maximum']
        )
        metrics['healthy_host_count'] = response.get('Datapoints', [])
    except Exception as e:
        metrics['healthy_host_count_error'] = str(e)
    
    # Get TargetResponseTime
    try:
        response = cw.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName='TargetResponseTime',
            Dimensions=[
                {'Name': 'TargetGroup', 'Value': target_group_arn.split('/')[-1]}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Average', 'Maximum', 'p99']
        )
        metrics['target_response_time'] = response.get('Datapoints', [])
    except Exception as e:
        metrics['target_response_time_error'] = str(e)
    
    # Get HTTPCode_Target_5XX_Count
    try:
        response = cw.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName='HTTPCode_Target_5XX_Count',
            Dimensions=[
                {'Name': 'TargetGroup', 'Value': target_group_arn.split('/')[-1]}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=['Sum']
        )
        metrics['http_5xx_count'] = response.get('Datapoints', [])
    except Exception as e:
        metrics['http_5xx_count_error'] = str(e)
    
    return metrics


def check_flapping(
    health_history: List[Dict[str, Any]],
    threshold: int = 3
) -> bool:
    """Check if target is flapping (healthy/unhealthy cycles)."""
    if len(health_history) < threshold * 2:
        return False
    
    state_changes = 0
    for i in range(1, len(health_history)):
        prev_state = health_history[i-1].get('state', '')
        curr_state = health_history[i].get('state', '')
        if prev_state != curr_state:
            state_changes += 1
    
    return state_changes >= threshold


def calculate_diagnostic_score(diagnostics: Dict[str, Any]) -> float:
    """Calculate diagnostic score (0-100, lower is worse)."""
    score = 100.0
    
    # Application failures
    if diagnostics.get('application_failure', False):
        score -= 40
    
    # Resource bottlenecks
    cpu_usage = diagnostics.get('cpu_usage', 0)
    if cpu_usage > 90:
        score -= 20
    elif cpu_usage > 80:
        score -= 10
    
    memory_usage = diagnostics.get('memory_usage', 0)
    if memory_usage > 90:
        score -= 20
    elif memory_usage > 80:
        score -= 10
    
    # Disk issues
    if diagnostics.get('disk_corruption', False):
        score -= 30
    
    # Network issues
    if diagnostics.get('network_degradation', False):
        score -= 15
    
    # Agent failures
    if diagnostics.get('ssm_agent_failure', False):
        score -= 25
    if diagnostics.get('cloudwatch_agent_failure', False):
        score -= 10
    
    return max(0.0, score)


def should_replace_instance(diagnostic_score: float, repair_attempts: int) -> bool:
    """Determine if instance should be replaced."""
    # Replace if diagnostic score is very low
    if diagnostic_score < 30:
        return True
    
    # Replace if multiple repair attempts failed
    if repair_attempts >= 2:
        return True
    
    return False

