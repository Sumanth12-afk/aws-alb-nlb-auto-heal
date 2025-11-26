"""Structured logging utilities."""
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """Structured JSON logger for Lambda functions."""
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Add console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)
    
    def _format_message(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Format log message as structured JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'message': message,
            'service': os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
            'request_id': os.environ.get('AWS_REQUEST_ID', 'unknown'),
        }
        log_entry.update(kwargs)
        return log_entry
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        log_entry = self._format_message('INFO', message, **kwargs)
        self.logger.info(json.dumps(log_entry))
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        log_entry = self._format_message('ERROR', message, **kwargs)
        self.logger.error(json.dumps(log_entry))
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        log_entry = self._format_message('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(log_entry))
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        log_entry = self._format_message('DEBUG', message, **kwargs)
        self.logger.debug(json.dumps(log_entry))


def get_logger(name: str = __name__) -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name)

