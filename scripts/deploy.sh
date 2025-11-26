#!/bin/bash
# Deployment script for Dynamic Auto-Heal system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infra/terraform"

echo "=========================================="
echo "Dynamic Auto-Heal Deployment Script"
echo "=========================================="

# Check for required tools
command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is required but not installed. Aborting." >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "Error: AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required but not installed. Aborting." >&2; exit 1; }

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured. Please run 'aws configure'." >&2
    exit 1
fi

# Parse command line arguments
ENVIRONMENT="${1:-prod}"
ACTION="${2:-plan}"

if [ "$ACTION" != "plan" ] && [ "$ACTION" != "apply" ] && [ "$ACTION" != "destroy" ]; then
    echo "Usage: $0 [environment] [plan|apply|destroy]"
    echo "  environment: dev, staging, or prod (default: prod)"
    echo "  action: plan, apply, or destroy (default: plan)"
    exit 1
fi

echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo ""

# Navigate to Terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Create terraform.tfvars if it doesn't exist
if [ ! -f "terraform.tfvars" ]; then
    echo "Creating terraform.tfvars from template..."
    cat > terraform.tfvars <<EOF
aws_region = "us-east-1"
environment = "$ENVIRONMENT"
target_group_arns = []
monitoring_interval_minutes = 5
sns_topic_arn = ""
health_check_endpoint = "/health"
health_check_port = "80"
lambda_timeout = 300
lambda_memory_size = 512
enable_vpc = false
event_bus_name = "default"
EOF
    echo "Please edit terraform.tfvars with your configuration before deploying."
    exit 1
fi

# Run Terraform action
case "$ACTION" in
    plan)
        echo "Running Terraform plan..."
        terraform plan -var="environment=$ENVIRONMENT" -out=tfplan
        echo ""
        echo "Plan complete. Review the plan above."
        echo "To apply: $0 $ENVIRONMENT apply"
        ;;
    apply)
        echo "Applying Terraform configuration..."
        if [ -f "tfplan" ]; then
            terraform apply tfplan
        else
            terraform apply -var="environment=$ENVIRONMENT" -auto-approve
        fi
        echo ""
        echo "Deployment complete!"
        echo ""
        echo "Next steps:"
        echo "1. Configure target group ARNs in terraform.tfvars"
        echo "2. Set up SNS topic subscriptions for notifications"
        echo "3. Test the system with a manual Lambda invocation"
        ;;
    destroy)
        echo "WARNING: This will destroy all resources!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "Aborted."
            exit 0
        fi
        terraform destroy -var="environment=$ENVIRONMENT" -auto-approve
        echo "Teardown complete!"
        ;;
esac

echo ""
echo "Done!"

