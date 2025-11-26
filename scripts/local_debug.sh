#!/bin/bash
# Local debugging script for Lambda functions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Dynamic Auto-Heal Local Debug Script"
echo "=========================================="

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required but not installed. Aborting." >&2; exit 1; }

# Parse command line arguments
FUNCTION="${1:-target_monitor}"
EVENT_FILE="${2:-test_event.json}"

if [ ! -f "$PROJECT_ROOT/$EVENT_FILE" ]; then
    echo "Creating sample test event file: $EVENT_FILE"
    cat > "$PROJECT_ROOT/$EVENT_FILE" <<EOF
{
  "source": "manual",
  "target_groups": [],
  "instance_id": "i-1234567890abcdef0",
  "target_group_arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/test-tg/1234567890123456",
  "issue_type": "unhealthy_target",
  "classification": "Application Failure",
  "diagnostic_score": 45.0
}
EOF
    echo "Sample event file created. Please edit it with your test data."
fi

# Set up Python path
export PYTHONPATH="$PROJECT_ROOT/src/lambda:$PYTHONPATH"

# Set environment variables
export AWS_REGION="${AWS_REGION:-us-east-1}"
export TARGET_HEALTH_TABLE="test-target-health-events"
export DIAGNOSTICS_TABLE="test-diagnostics-history"
export AUTO_HEAL_TABLE="test-auto-heal-history"
export INSTANCE_CONFIG_TABLE="test-instance-config"
export VERIFICATION_TABLE="test-verification-history"
export EVENT_BUS_NAME="default"
export SSM_DIAGNOSTICS_DOCUMENT="test-diagnostics"
export SSM_REPAIR_DOCUMENT="test-repair"
export SSM_VERIFY_DOCUMENT="test-verify"
export HEALTH_CHECK_ENDPOINT="/health"
export HEALTH_CHECK_PORT="80"
export SNS_TOPIC_ARN=""

# Function directory
FUNCTION_DIR="$PROJECT_ROOT/src/lambda/$FUNCTION"

if [ ! -d "$FUNCTION_DIR" ]; then
    echo "Error: Function directory not found: $FUNCTION_DIR"
    echo "Available functions: target_monitor, diagnostics, auto_heal, verify"
    exit 1
fi

echo "Function: $FUNCTION"
echo "Event file: $EVENT_FILE"
echo ""

# Run the handler
cd "$FUNCTION_DIR"

echo "Running handler with test event..."
echo ""

python3 -c "
import json
import sys
sys.path.insert(0, '$PROJECT_ROOT/src/lambda')

from handler import lambda_handler

with open('$PROJECT_ROOT/$EVENT_FILE', 'r') as f:
    event = json.load(f)

try:
    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo ""
echo "Debug run complete!"

