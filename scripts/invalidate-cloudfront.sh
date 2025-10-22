#!/bin/bash

# Script to invalidate CloudFront cache for hackathon environment
# Usage: ./invalidate-cloudfront.sh [environment] [paths]

set -euo pipefail

ENVIRONMENT=${1:-hackathon}
PATHS=${2:-"/*"}

echo "🔄 Invalidating CloudFront cache for $ENVIRONMENT environment..."
echo "Paths: $PATHS"
echo ""

# Find CloudFront distribution
echo "🔍 Finding CloudFront distribution..."
DISTRIBUTION_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Aliases.Items[?contains(@, 'app.${ENVIRONMENT}.agentleague.ai')]].Id | [0]" \
  --output text)

if [ -n "$DISTRIBUTION_ID" ] && [ "$DISTRIBUTION_ID" != "None" ]; then
  echo "✅ Found distribution: $DISTRIBUTION_ID"
  echo ""
  echo "🔄 Creating invalidation..."
  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "$PATHS" \
    --query 'Invalidation.Id' \
    --output text)
  
  echo "✅ Invalidation created: $INVALIDATION_ID"
  echo ""
  echo "To check invalidation status:"
  echo "  aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id $INVALIDATION_ID"
else
  echo "❌ CloudFront distribution not found for app.${ENVIRONMENT}.agentleague.ai"
  echo ""
  echo "Available distributions:"
  aws cloudfront list-distributions \
    --query 'DistributionList.Items[*].[Id, Aliases.Items[0]]' \
    --output table
  exit 1
fi

