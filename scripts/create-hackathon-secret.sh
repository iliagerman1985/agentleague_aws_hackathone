#!/bin/bash

# Script to create AWS Secrets Manager secret for hackathon environment
# This script creates a secret named 'hackathon_secret' with database credentials and other sensitive data

set -euo pipefail

# Configuration
SECRET_NAME="hackathon_secret"
AWS_REGION="us-east-1"

echo "🔐 Creating AWS Secrets Manager secret: $SECRET_NAME"
echo "Region: $AWS_REGION"
echo ""

# Check if secret already exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo "⚠️  Secret '$SECRET_NAME' already exists!"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted"
        exit 1
    fi
    UPDATE_MODE=true
else
    UPDATE_MODE=false
fi

# Generate random passwords
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)

echo "📝 Generated secure random passwords"
echo ""

# Create secret JSON
SECRET_JSON=$(cat <<EOF
{
  "database": {
    "username": "postgres",
    "password": "$DB_PASSWORD",
    "host": "postgres.hackathon.local",
    "port": 5432,
    "name": "agentleague",
    "url": "postgresql://postgres:$DB_PASSWORD@postgres.hackathon.local:5432/agentleague"
  },
  "security": {
    "secret_key": "$SECRET_KEY"
  },
  "aws": {
    "cognito_client_secret": ""
  },
  "stripe": {
    "api_key": "",
    "webhook_secret": "",
    "success_url": "https://app.hackathon.agentleague.ai/billing/success",
    "cancel_url": "https://app.hackathon.agentleague.ai/billing/cancel"
  },
  "llm_providers": {
    "openai": {
      "api_key": ""
    },
    "anthropic": {
      "api_key": ""
    }
  }
}
EOF
)

# Create or update secret
if [ "$UPDATE_MODE" = true ]; then
    echo "🔄 Updating secret..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_JSON" \
        --region "$AWS_REGION"
    echo "✅ Secret updated successfully!"
else
    echo "🆕 Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Secrets for AgentLeague hackathon environment" \
        --secret-string "$SECRET_JSON" \
        --region "$AWS_REGION"
    echo "✅ Secret created successfully!"
fi

echo ""
echo "📋 Secret Details:"
echo "  Name: $SECRET_NAME"
echo "  Region: $AWS_REGION"
echo "  Database Password: $DB_PASSWORD"
echo ""
echo "⚠️  IMPORTANT: Save the database password securely!"
echo "⚠️  You will need to manually add Stripe and LLM provider API keys to the secret"
echo ""
echo "To view the secret:"
echo "  aws secretsmanager get-secret-value --secret-id $SECRET_NAME --region $AWS_REGION"
echo ""
echo "To update specific values:"
echo "  aws secretsmanager update-secret --secret-id $SECRET_NAME --secret-string '{...}' --region $AWS_REGION"

