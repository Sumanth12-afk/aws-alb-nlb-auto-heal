"""Repair priority calculation logic."""
from typing import Dict, Any, List
from enum import IntEnum


class FailurePriority(IntEnum):
    """Failure priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    UNKNOWN = 0


PRIORITY_MAP = {
    'Application Failure': FailurePriority.CRITICAL,
    'OS-level Failure': FailurePriority.CRITICAL,
    'Disk Corruption': FailurePriority.CRITICAL,
    'Agent Failure': FailurePriority.HIGH,
    'Resource Bottleneck': FailurePriority.MEDIUM,
    'Network Degradation': FailurePriority.MEDIUM,
    'Unknown State': FailurePriority.UNKNOWN
}


def calculate_repair_priority(
    classification: str,
    diagnostic_score: float,
    repair_attempts: int
) -> int:
    """
    Calculate repair priority based on classification and context.
    
    Returns priority value (lower = higher priority).
    """
    base_priority = PRIORITY_MAP.get(classification, FailurePriority.UNKNOWN)
    
    # Adjust based on diagnostic score
    if diagnostic_score < 20:
        base_priority = FailurePriority.CRITICAL
    elif diagnostic_score < 40:
        base_priority = min(base_priority, FailurePriority.HIGH)
    
    # Adjust based on repair attempts
    if repair_attempts >= 2:
        base_priority = FailurePriority.CRITICAL
    
    return int(base_priority)


def should_skip_repair(
    classification: str,
    diagnostic_score: float,
    instance_config: Dict[str, Any]
) -> bool:
    """Determine if repair should be skipped."""
    # Skip if explicitly configured
    if instance_config.get('skip_recovery', False):
        return True
    
    # Skip if diagnostic score is extremely low (likely unrecoverable)
    if diagnostic_score < 10:
        return True
    
    # Skip if classification indicates replacement needed
    if classification in ['OS-level Failure', 'Disk Corruption']:
        return True
    
    return False


def get_repair_timeout(classification: str) -> int:
    """Get repair timeout in seconds based on classification."""
    timeouts = {
        'Application Failure': 300,  # 5 minutes
        'Resource Bottleneck': 600,  # 10 minutes
        'Agent Failure': 900,  # 15 minutes
        'Network Degradation': 600,
        'OS-level Failure': 0,  # Should not repair
        'Disk Corruption': 0,  # Should not repair
        'Unknown State': 300
    }
    
    return timeouts.get(classification, 300)

