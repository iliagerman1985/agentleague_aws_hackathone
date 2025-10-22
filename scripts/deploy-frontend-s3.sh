#!/bin/bash

# Script to deploy frontend to S3 and invalidate CloudFront cache
# Usage: ./deploy-frontend-s3.sh [environment] [distribution_id]

set -euo pipefail

ENVIRONMENT=${1:-hackathon}
BUCKET_NAME="agentleague-${ENVIRONMENT}-frontend"
DISTRIBUTION_ID=${2:-}

echo "🚀 Deploying frontend to S3..."
echo "Environment: $ENVIRONMENT"
echo "Bucket: $BUCKET_NAME"
echo ""

# Check if client directory exists
if [ ! -d "client" ]; then
    echo "❌ Error: client directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Build frontend
echo "📦 Installing dependencies..."
cd client
npm ci

echo "🏗️  Building frontend for $ENVIRONMENT..."
if [ "$ENVIRONMENT" = "hackathon" ]; then
    npm run build:s3
else
    npm run build
fi

echo "✅ Frontend build complete"
ls -lah dist/

# Upload to S3
echo ""
echo "📤 Uploading to S3 bucket: $BUCKET_NAME"

# Upload all files except index.html and manifest.json with long cache
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html" \
  --exclude "manifest.json"

# Upload index.html with no-cache
aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html \
  --cache-control "public, max-age=0, must-revalidate"

# Upload manifest.json with no-cache (if exists)
if [ -f dist/manifest.json ]; then
    aws s3 cp dist/manifest.json s3://$BUCKET_NAME/manifest.json \
      --cache-control "public, max-age=0, must-revalidate"
fi

echo "✅ Frontend uploaded to S3"

# Invalidate CloudFront
if [ -z "$DISTRIBUTION_ID" ]; then
  echo ""
  echo "🔍 Finding CloudFront distribution..."
  DISTRIBUTION_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?Aliases.Items[?contains(@, 'app.${ENVIRONMENT}.agentleague.ai')]].Id | [0]" \
    --output text)
fi

if [ -n "$DISTRIBUTION_ID" ] && [ "$DISTRIBUTION_ID" != "None" ]; then
  echo "🔄 Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*"
  echo "✅ CloudFront cache invalidated for distribution: $DISTRIBUTION_ID"
else
  echo "⚠️  CloudFront distribution not found"
  echo "You may need to manually invalidate the cache"
  exit 1
fi

cd ..
echo ""
echo "🎉 Deployment complete!"
echo "Frontend URL: https://app.${ENVIRONMENT}.agentleague.ai"

