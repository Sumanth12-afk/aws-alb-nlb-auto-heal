#!/bin/bash
# Teardown script for Dynamic Auto-Heal system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform"

echo "=========================================="
echo "Dynamic Auto-Heal Teardown Script"
echo "=========================================="

# Check for required tools
command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is required but not installed. Aborting." >&2; exit 1; }

# Parse command line arguments
ENVIRONMENT="${1:-prod}"

echo "Environment: $ENVIRONMENT"
echo ""
echo "WARNING: This will destroy all resources for the $ENVIRONMENT environment!"
echo "This includes:"
echo "  - Lambda functions"
echo "  - DynamoDB tables"
echo "  - EventBridge rules"
echo "  - SSM documents"
echo "  - IAM roles and policies"
echo "  - SNS topics"
echo ""
read -p "Are you absolutely sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "Teardown aborted."
    exit 0
fi

# Navigate to Terraform directory
cd "$TERRAFORM_DIR"

# Destroy infrastructure
echo "Destroying infrastructure..."
terraform destroy -var="environment=$ENVIRONMENT" -auto-approve

echo ""
echo "Teardown complete!"
echo "All resources have been destroyed."

