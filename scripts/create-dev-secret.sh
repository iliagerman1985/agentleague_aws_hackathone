#!/bin/bash

# Script to create the dev_secret in AWS Secrets Manager
# This script uploads the development secrets to AWS Secrets Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration (can be overridden by environment variables)
PROJECT_NAME="${PROJECT_NAME:-agentleague}"
ENVIRONMENT="${APP_ENV:-development}"
SECRET_NAME="dev_secret"  # Fixed name that matches config service expectation
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
SECRETS_FILE="libs/common/secrets.yaml"

log_info "Creating AWS Secrets Manager secret: $SECRET_NAME"

# Function to create empty secret template
create_empty_secret() {
    cat << 'EOF'
# Development secrets file - AWS deployment
# Please update with your actual secrets

# Database credentials and connection information
database:
  # Connection string for Docker Compose PostgreSQL with pgvector
  # Use localhost when backend runs in host network mode
  url: "postgresql://postgres:postgres123@localhost:5432/agent_league"

security:
  secret_key: "CHANGE_ME_dev_secret_key_for_aws_development"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  encryption_key: "CHANGE_ME_base64_encoded_encryption_key"

# LLM Provider API Keys and Configuration
llm_providers:
  # OpenAI Configuration
  openai:
    api_key: "CHANGE_ME_openai_api_key"
    organization: ""
    base_url: "https://api.openai.com/v1"

  # Anthropic Configuration
  anthropic:
    api_key: "CHANGE_ME_anthropic_api_key"
    base_url: "https://api.anthropic.com"

  # Google Gemini Configuration
  gemini:
    api_key: "CHANGE_ME_gemini_api_key"
    base_url: "https://generativelanguage.googleapis.com"

  aws_bedrock:
    api_key: "CHANGE_ME_bedrock_api_key"

# AWS credentials for SQS and other services
aws:
  access_key_id: "CHANGE_ME_aws_access_key"
  secret_access_key: "CHANGE_ME_aws_secret_key"
  region: "us-east-1"
  cognito_client_secret: "CHANGE_ME_cognito_client_secret"

# SQS Queue URLs (will be populated by Terraform outputs)
sqs:
  process_message_queue_url: ""
  process_message_dead_letter_queue_url: ""
  billing_events_queue_url: ""
  webhooks_queue_url: ""

opencode:
  access_key_id: "CHANGE_ME_opencode_access_key"
  secret_access_key: "CHANGE_ME_opencode_secret_key"
  region: "us-west-2"

openai:
  api_key: "CHANGE_ME_legacy_openai_api_key"
EOF
}

# Determine secret content source
if [ -f "$SECRETS_FILE" ]; then
    log_info "Found existing secrets file: $SECRETS_FILE"
    log_info "Reading secrets from local file..."
    SECRET_CONTENT=$(cat "$SECRETS_FILE")

    # Add SQS queue URLs section if not present
    if ! grep -q "sqs:" "$SECRETS_FILE"; then
        log_info "Adding SQS queue URLs section to secrets..."
        SECRET_CONTENT="$SECRET_CONTENT

# SQS Queue URLs (will be populated by Terraform outputs)
sqs:
  process_message_queue_url: \"\"
  process_message_dead_letter_queue_url: \"\"
  billing_events_queue_url: \"\"
  webhooks_queue_url: \"\""
    fi
else
    log_warning "Secrets file not found: $SECRETS_FILE"
    log_info "Creating empty secret template..."
    SECRET_CONTENT=$(create_empty_secret)
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS CLI is not configured or credentials are invalid"
    log_info "Please run 'aws configure' or set up your AWS credentials"
    exit 1
fi

log_info "AWS CLI configured successfully"

# Check if secret already exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    log_warning "Secret $SECRET_NAME already exists"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Updating existing secret..."
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "$SECRET_CONTENT" \
            --region "$AWS_REGION"
        log_success "Secret $SECRET_NAME updated successfully"
    else
        log_info "Skipping secret update"
        exit 0
    fi
else
    log_info "Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Development secrets for AgentLeague application" \
        --secret-string "$SECRET_CONTENT" \
        --region "$AWS_REGION"
    log_success "Secret $SECRET_NAME created successfully"
fi

# Test secret retrieval
log_info "Testing secret retrieval..."
if aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query 'SecretString' --output text > /dev/null; then
    log_success "Secret retrieval test passed"
else
    log_error "Secret retrieval test failed"
    exit 1
fi

log_success "✅ AWS Secrets Manager setup complete!"
log_info "Secret name: $SECRET_NAME"
log_info "Region: $AWS_REGION"
log_info ""
log_info "The secret is now ready for use by your AWS deployment."
log_info "Your application will automatically load this secret when deployed to AWS."
