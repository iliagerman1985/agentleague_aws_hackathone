#!/bin/bash

# Script to set up AWS Secrets Manager with application secrets
# This script reads from your local secrets.yaml and creates/updates the AWS secret

set -e

# Configuration
PROJECT_NAME="agentleague"
AWS_REGION="us-east-1"
SECRET_NAME="${PROJECT_NAME}-secrets"
LOCAL_SECRETS_FILE="libs/common/secrets.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log with colors
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if local secrets file exists
if [ ! -f "$LOCAL_SECRETS_FILE" ]; then
    log_error "Local secrets file not found: $LOCAL_SECRETS_FILE"
    log_info "Please create the secrets file based on libs/common/secrets.example.yaml"
    exit 1
fi

# Check AWS credentials
log_info "Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    log_info "Please run 'aws configure' to set up your credentials"
    exit 1
fi

log_info "AWS credentials verified"

# Check if secret already exists
log_info "Checking if secret already exists..."
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    log_warn "Secret '$SECRET_NAME' already exists"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Aborted by user"
        exit 0
    fi
    UPDATE_SECRET=true
else
    log_info "Secret does not exist, will create new one"
    UPDATE_SECRET=false
fi

# Validate YAML file
log_info "Validating local secrets file..."
if ! python3 -c "import yaml; yaml.safe_load(open('$LOCAL_SECRETS_FILE'))" 2>/dev/null; then
    log_error "Invalid YAML in secrets file: $LOCAL_SECRETS_FILE"
    exit 1
fi

log_info "YAML file is valid"

# Create or update the secret
if [ "$UPDATE_SECRET" = true ]; then
    log_info "Updating existing secret..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string file://"$LOCAL_SECRETS_FILE" \
        --region "$AWS_REGION" > /dev/null
    
    log_info "✅ Secret updated successfully"
else
    log_info "Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Application secrets for $PROJECT_NAME dev environment" \
        --secret-string file://"$LOCAL_SECRETS_FILE" \
        --region "$AWS_REGION" > /dev/null
    
    log_info "✅ Secret created successfully"
fi

# Get the secret ARN
SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query 'ARN' --output text)

log_info "Secret ARN: $SECRET_ARN"

# Test retrieving the secret
log_info "Testing secret retrieval..."
if aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query 'SecretString' --output text > /dev/null; then
    log_info "✅ Secret retrieval test successful"
else
    log_error "❌ Secret retrieval test failed"
    exit 1
fi

# Show summary
echo
log_info "=== Setup Summary ==="
log_info "Secret Name: $SECRET_NAME"
log_info "Secret ARN: $SECRET_ARN"
log_info "AWS Region: $AWS_REGION"
echo
log_info "Your application can now retrieve secrets using:"
log_info "aws secretsmanager get-secret-value --secret-id $SECRET_NAME --region $AWS_REGION"
echo
log_info "Make sure your EC2 instance has the following IAM permission:"
log_info "secretsmanager:GetSecretValue on resource: $SECRET_ARN"

# Optional: Show what's in the secret (without sensitive values)
echo
read -p "Do you want to see the secret structure (without sensitive values)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Secret structure:"
    python3 -c "
import yaml
import json

def mask_sensitive_values(obj, path=''):
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            current_path = f'{path}.{key}' if path else key
            if any(sensitive in key.lower() for sensitive in ['password', 'key', 'secret', 'token']):
                result[key] = '***MASKED***'
            else:
                result[key] = mask_sensitive_values(value, current_path)
        return result
    elif isinstance(obj, list):
        return [mask_sensitive_values(item, f'{path}[{i}]') for i, item in enumerate(obj)]
    else:
        return obj

with open('$LOCAL_SECRETS_FILE', 'r') as f:
    secrets = yaml.safe_load(f)
    masked = mask_sensitive_values(secrets)
    print(yaml.dump(masked, default_flow_style=False, indent=2))
"
fi

log_info "🎉 Secrets setup completed successfully!"
