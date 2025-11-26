"""Slack notification Lambda handler - sends SNS messages to Slack."""
import json
import os
import urllib.request
import urllib.error
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')
SLACK_USERNAME = os.environ.get('SLACK_USERNAME', 'Auto-Heal Bot')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process SNS message and send to Slack.
    
    Triggered by SNS topic subscription.
    """
    logger.info(f"Slack notifier started: {json.dumps(event)}")
    
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL not configured")
        return {'statusCode': 400, 'body': 'Slack webhook URL not configured'}
    
    try:
        # Parse SNS event
        for record in event.get('Records', []):
            if record.get('EventSource') != 'aws:sns':
                continue
            
            sns_message = record.get('Sns', {})
            subject = sns_message.get('Subject', 'Auto-Heal Notification')
            message = sns_message.get('Message', '')
            
            # Parse message if it's JSON
            message_data = None
            try:
                message_data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                # Try to parse malformed JSON (keys without quotes)
                try:
                    # Replace unquoted keys with quoted keys
                    import re
                    # Pattern: word followed by colon (but not already quoted)
                    fixed_message = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', message)
                    # Fix string values that aren't quoted
                    fixed_message = re.sub(r':\s*([a-zA-Z0-9_/-]+)([,}])', r': "\1"\2', fixed_message)
                    # Fix boolean and numeric values
                    fixed_message = re.sub(r':\s*(true|false|null)([,}])', r': \1\2', fixed_message)
                    fixed_message = re.sub(r':\s*([0-9]+\.?[0-9]*)([,}])', r': \1\2', fixed_message)
                    message_data = json.loads(fixed_message)
                    logger.info(f"Successfully parsed malformed JSON")
                except Exception as e:
                    logger.warning(f"Could not parse message as JSON: {str(e)}")
                    # Try to parse as dict if it's already a dict
                    if isinstance(message, dict):
                        message_data = message
                    else:
                        # Last resort: try to extract key-value pairs manually
                        message_data = _parse_pseudo_json(message)
            
            if message_data:
                formatted_message = _format_message(message_data, subject)
            else:
                formatted_message = _format_simple_message(message, subject)
            
            # Send to Slack
            _send_to_slack(formatted_message, subject)
        
        return {'statusCode': 200, 'body': 'Message sent to Slack'}
    
    except Exception as e:
        logger.error(f"Slack notifier failed: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}


def _format_message(message_data: Dict[str, Any], subject: str) -> Dict[str, Any]:
    """Format message data into Slack message format."""
    # Extract key information
    instance_id = message_data.get('instance_id', 'Unknown')
    target_group_arn = message_data.get('target_group_arn', 'Unknown')
    event_type = message_data.get('event_type', 'unknown')
    timestamp = message_data.get('timestamp', '')
    message_text = message_data.get('message', '')
    
    # Build Slack message
    color = _get_color_for_event(event_type)
    
    # Build main text with emoji based on event type
    emoji_map = {
        'unhealthy_target': '🚨',
        'degraded_target': '⚠️',
        'flapping_target': '🔄',
        'diagnostics_complete': '🔍',
        'auto_heal_complete': '✅',
        'verification_complete': '✓',
        'verification_failed': '❌'
    }
    emoji = emoji_map.get(event_type, '📢')
    
    fields = []
    
    if instance_id != 'Unknown':
        fields.append({
            "title": "🖥️ Instance ID",
            "value": f"`{instance_id}`",
            "short": True
        })
    
    if target_group_arn != 'Unknown':
        tg_name = target_group_arn.split('/')[-1] if '/' in target_group_arn else target_group_arn
        fields.append({
            "title": "🎯 Target Group",
            "value": f"`{tg_name}`",
            "short": True
        })
    
    if message_data.get('classification'):
        fields.append({
            "title": "🔬 Classification",
            "value": f"*{message_data.get('classification')}*",
            "short": True
        })
    
    if message_data.get('diagnostic_score') is not None:
        score = float(message_data.get('diagnostic_score', 100))
        score_emoji = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
        fields.append({
            "title": "📊 Diagnostic Score",
            "value": f"{score_emoji} {score:.1f}/100",
            "short": True
        })
    
    if message_data.get('action'):
        action_emoji = "🔧" if message_data.get('action') == 'repair' else "🔄"
        fields.append({
            "title": "⚡ Action Taken",
            "value": f"{action_emoji} {message_data.get('action').upper()}",
            "short": True
        })
    
    if message_data.get('all_checks_passed') is not None:
        status = "✅ Passed" if message_data.get('all_checks_passed') else "❌ Failed"
        fields.append({
            "title": "✔️ Verification",
            "value": status,
            "short": True
        })
    
    # Add custom message if provided
    if message_text:
        # Clean emojis from message text to avoid encoding issues
        import re
        # Remove emoji characters (Unicode ranges for emojis)
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        clean_message = emoji_pattern.sub('', message_text).strip()
        # Add back a simple prefix if message had emoji
        if clean_message != message_text:
            clean_message = "• " + clean_message
        fields.append({
            "title": "📝 Details",
            "value": clean_message,
            "short": False
        })
    
    attachment = {
        "color": color,
        "title": f"{emoji} {subject}",
        "fields": fields,
        "footer": "Dynamic Auto-Heal System | AWS",
        "footer_icon": "https://a.slack-edge.com/80588/img/services/aws_72.png",
        "ts": _get_timestamp(timestamp)
    }
    
    return {
        "text": f"{emoji} *{subject}*",
        "attachments": [attachment],
        "channel": SLACK_CHANNEL,
        "username": SLACK_USERNAME
    }


def _parse_pseudo_json(message: str) -> Dict[str, Any]:
    """Parse pseudo-JSON format (keys without quotes) into a dict."""
    result = {}
    try:
        # Remove outer braces
        content = message.strip().strip('{}')
        # Split by comma, but be careful with nested structures
        import re
        # Match key:value pairs
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([^,}]+?)(?=,\s*[a-zA-Z_]|$)'
        matches = re.findall(pattern, content)
        for key, value in matches:
            value = value.strip().strip('"\'')
            # Try to convert to appropriate type
            if value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            elif value.replace('.', '', 1).isdigit():
                result[key] = float(value) if '.' in value else int(value)
            else:
                result[key] = value
    except Exception as e:
        logger.warning(f"Failed to parse pseudo-JSON: {str(e)}")
    return result


def _format_simple_message(message: str, subject: str) -> Dict[str, Any]:
    """Format simple text message for Slack."""
    return {
        "text": f"*{subject}*\n\n{message}",
        "channel": SLACK_CHANNEL,
        "username": SLACK_USERNAME
    }


def _get_color_for_event(event_type: str) -> str:
    """Get color for Slack message based on event type."""
    color_map = {
        'target_health_issue': 'warning',
        'unhealthy_target': 'danger',  # Red
        'degraded_target': 'warning',  # Yellow
        'flapping_target': 'warning',  # Yellow
        'diagnostics_complete': '#36a64f',  # Green
        'auto_heal_complete': '#36a64f',  # Green
        'verification_complete': '#36a64f',  # Green
        'verification_failed': 'danger',  # Red
        'system_ready': '#36a64f',  # Green
        'test': '#439FE0'  # Blue
    }
    return color_map.get(event_type, '#36a64f')


def _get_timestamp(timestamp: str) -> int:
    """Convert ISO timestamp to Unix timestamp."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except:
        import time
        return int(time.time())


def _send_to_slack(message: Dict[str, Any], subject: str):
    """Send message to Slack via webhook."""
    try:
        payload = json.dumps(message).encode('utf-8')
        
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            response_text = response.read().decode('utf-8')
            logger.info(f"Message sent to Slack - Subject: {subject}, Response: {response_text}")
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Slack webhook HTTP error - Status: {e.code}, Error: {error_body}")
        raise
    
    except Exception as e:
        logger.error(f"Failed to send message to Slack: {str(e)}")
        raise

