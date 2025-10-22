#!/bin/bash
# Build script for AgentCore Docker image

set -e

# Configuration
IMAGE_NAME="agentleague-agentcore"
REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME=${PROJECT_NAME:-agentleague}

# Get version from environment or use timestamp
VERSION=${VERSION:-$(date +%Y%m%d-%H%M%S)}
ECR_TAG="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-agentcore:${VERSION}"
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-agentcore"

echo "Building AgentCore Docker image..."
echo "Image: ${ECR_TAG}"
echo "Local tag: ${IMAGE_NAME}:${VERSION}"

# Build the Docker image
docker build -f backend/Dockerfile.agentcore -t ${IMAGE_NAME}:${VERSION} backend/
docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest
docker tag ${IMAGE_NAME}:${VERSION} ${ECR_TAG}
docker tag ${IMAGE_NAME}:latest ${ECR_REPO}:latest

echo "Build completed successfully!"
echo "Local image: ${IMAGE_NAME}:${VERSION}"
echo "ECR tag: ${ECR_TAG}"

# If in GitHub Actions, also output the tag
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "image-tag=${ECR_TAG}" >> $GITHUB_OUTPUT
    echo "local-tag=${IMAGE_NAME}:${VERSION}" >> $GITHUB_OUTPUT
fi

echo "To push to ECR, run: ./scripts/deploy-agentcore.sh ${VERSION}"