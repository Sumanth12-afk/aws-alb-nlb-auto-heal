"""Decision model for auto-heal actions."""
from typing import Dict, Any, Optional
from .repair_priority import (
    calculate_repair_priority,
    should_skip_repair,
    get_repair_timeout
)


def should_replace_instance(diagnostic_score: float, repair_attempts: int) -> bool:
    """Determine if instance should be replaced."""
    # Replace if diagnostic score is very low
    if diagnostic_score < 30:
        return True
    
    # Replace if multiple repair attempts failed
    if repair_attempts >= 2:
        return True
    
    return False


class AutoHealDecision:
    """Auto-heal decision model."""
    
    def __init__(
        self,
        instance_id: str,
        classification: str,
        diagnostic_score: float,
        repair_attempts: int,
        instance_config: Dict[str, Any]
    ):
        self.instance_id = instance_id
        self.classification = classification
        self.diagnostic_score = diagnostic_score
        self.repair_attempts = repair_attempts
        self.instance_config = instance_config
    
    def decide(self) -> Dict[str, Any]:
        """Make auto-heal decision."""
        decision = {
            'instance_id': self.instance_id,
            'action': None,
            'reason': '',
            'priority': 0,
            'timeout_seconds': 0,
            'skip': False
        }
        
        # Check if should skip
        if should_skip_repair(
            self.classification,
            self.diagnostic_score,
            self.instance_config
        ):
            decision['skip'] = True
            decision['reason'] = 'Skipped per configuration or unrecoverable state'
            return decision
        
        # Calculate priority
        priority = calculate_repair_priority(
            self.classification,
            self.diagnostic_score,
            self.repair_attempts
        )
        decision['priority'] = priority
        
        # Decide: repair or replace
        should_replace = should_replace_instance(
            self.diagnostic_score,
            self.repair_attempts
        )
        
        if should_replace:
            decision['action'] = 'replace'
            decision['reason'] = f'Diagnostic score {self.diagnostic_score:.1f} and {self.repair_attempts} repair attempts indicate replacement needed'
            decision['timeout_seconds'] = 1800  # 30 minutes for replacement
        else:
            decision['action'] = 'repair'
            decision['reason'] = f'Attempting repair for {self.classification} (score: {self.diagnostic_score:.1f})'
            decision['timeout_seconds'] = get_repair_timeout(self.classification)
        
        return decision


def make_decision(
    instance_id: str,
    classification: str,
    diagnostic_score: float,
    repair_attempts: int,
    instance_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Make auto-heal decision."""
    decision_model = AutoHealDecision(
        instance_id=instance_id,
        classification=classification,
        diagnostic_score=diagnostic_score,
        repair_attempts=repair_attempts,
        instance_config=instance_config
    )
    
    return decision_model.decide()

