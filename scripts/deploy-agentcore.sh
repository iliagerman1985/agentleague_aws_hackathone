#!/bin/bash
# Deployment script for AgentCore to AWS

set -euo pipefail
set -x

# Configuration
IMAGE_NAME="agentleague-agentcore"
PROJECT_NAME=${PROJECT_NAME:-agentleague}
REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Defaults for environment and runtime name (allow sourcing from repo .env)
ENVIRONMENT=${ENVIRONMENT:-development}
if [ -f "libs/common/.env.${ENVIRONMENT}" ]; then
  set -a; . "libs/common/.env.${ENVIRONMENT}"; set +a
elif [ -f "libs/common/.env.development" ]; then
  set -a; . "libs/common/.env.development"; set +a
fi
RUNTIME_NAME=${RUNTIME_NAME:-"${AGENTCORE_RUNTIME_NAME:-${PROJECT_NAME:-agentleague}-${ENVIRONMENT}-runtime}"}

# Version/tag
VERSION=${1:-latest}
# Use AGENTCORE_REPO if set (from CI), otherwise construct default
if [ -n "${AGENTCORE_REPO:-}" ]; then
  ECR_TAG="${AGENTCORE_REPO}:${VERSION}"
  ECR_REPO="${AGENTCORE_REPO}"
else
  ECR_TAG="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-agentcore:${VERSION}"
  ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-agentcore"
fi

# Optional: existing runtime ARN provided by caller/CI
RUNTIME_ARN=${RUNTIME_ARN:-""}

# Ensure AgentCore commands are present
aws bedrock-agentcore-control help >/dev/null

# Ensure/derive runtime execution role (create if missing)
if [ -z "${AGENTCORE_ROLE_ARN:-}" ]; then
  ROLE_NAME="${AGENTCORE_ROLE_NAME:-${AGENTCORE_PROJECT_NAME:-${PROJECT_NAME}}-agentcore-runtime}"
  ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

  if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
    echo "Creating IAM role for AgentCore runtime: ${ROLE_NAME}"
    cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeRolePolicy",
      "Effect": "Allow",
      "Principal": { "Service": "bedrock-agentcore.amazonaws.com" },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": { "aws:SourceAccount": "${ACCOUNT_ID}" },
        "ArnLike": { "aws:SourceArn": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:*" }
      }
    }
  ]
}
EOF
    aws iam create-role \
      --role-name "${ROLE_NAME}" \
      --assume-role-policy-document file://trust-policy.json \
      --description "Execution role for Bedrock AgentCore runtime ${ROLE_NAME}"

    echo "Attaching inline execution policy to ${ROLE_NAME}"
    cat > runtime-exec-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "ECRImageAccess","Effect": "Allow","Action": ["ecr:BatchGetImage","ecr:GetDownloadUrlForLayer"],"Resource": ["arn:aws:ecr:${REGION}:${ACCOUNT_ID}:repository/*"]},
    {"Effect": "Allow","Action": ["ecr:GetAuthorizationToken"],"Resource": "*"},
    {"Effect": "Allow","Action": ["logs:DescribeLogStreams","logs:CreateLogGroup"],"Resource": ["arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*"]},
    {"Effect": "Allow","Action": ["logs:DescribeLogGroups"],"Resource": ["arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:*"]},
    {"Effect": "Allow","Action": ["logs:CreateLogStream","logs:PutLogEvents"],"Resource": ["arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]},
    {"Effect": "Allow","Action": ["xray:PutTraceSegments","xray:PutTelemetryRecords","xray:GetSamplingRules","xray:GetSamplingTargets"],"Resource": ["*"]},
    {"Effect": "Allow","Action": "cloudwatch:PutMetricData","Resource": "*","Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}},
    {"Sid": "GetAgentAccessToken","Effect": "Allow","Action": ["bedrock-agentcore:GetWorkloadAccessToken","bedrock-agentcore:GetWorkloadAccessTokenForJWT","bedrock-agentcore:GetWorkloadAccessTokenForUserId"],"Resource": ["arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:workload-identity-directory/default","arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:workload-identity-directory/default/workload-identity/*"]},
    {"Sid": "BedrockModelInvocation","Effect": "Allow","Action": ["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],"Resource": ["arn:aws:bedrock:*::foundation-model/*","arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:*"]}
  ]
}
EOF
    aws iam put-role-policy --role-name "${ROLE_NAME}" --policy-name "AgentCoreRuntimeExecutionPolicy" --policy-document file://runtime-exec-policy.json
  else
    echo "Using existing IAM role for AgentCore runtime: ${ROLE_NAME}"
  fi

  export AGENTCORE_ROLE_ARN="${ROLE_ARN}"
fi

echo "Deploying AgentCore to AWS..."
echo "Version: ${VERSION}"
echo "ECR Repository: ${ECR_REPO}"
echo "Environment: ${ENVIRONMENT}"
echo "Runtime Name: ${RUNTIME_NAME}"

# Build request bodies
cat > agentcore-update.json << EOF
{
  "agentRuntimeArtifact": {
    "containerConfiguration": { "containerUri": "${ECR_TAG}" }
  },
  "roleArn": "${AGENTCORE_ROLE_ARN}",
  "networkConfiguration": { "networkMode": "PUBLIC" },
  "environmentVariables": { "ENVIRONMENT": "${ENVIRONMENT}", "AWS_REGION": "${REGION}" }
}
EOF

cat > agentcore-create.json << EOF
{
  "agentRuntimeName": "${RUNTIME_NAME}",
  "agentRuntimeArtifact": {
    "containerConfiguration": { "containerUri": "${ECR_TAG}" }
  },
  "roleArn": "${AGENTCORE_ROLE_ARN}",
  "networkConfiguration": { "networkMode": "PUBLIC" },
  "environmentVariables": { "ENVIRONMENT": "${ENVIRONMENT}", "AWS_REGION": "${REGION}" }
}
EOF

# Deploy to AgentCore
if [ -n "${RUNTIME_ARN}" ]; then
  echo "Using existing Runtime ARN: ${RUNTIME_ARN}"
  RUNTIME_ID="${RUNTIME_ARN##*/}"
  echo "Updating runtime by ID: ${RUNTIME_ID}"
  aws bedrock-agentcore-control update-agent-runtime \
    --agent-runtime-id "${RUNTIME_ID}" \
    --cli-input-json file://agentcore-update.json \
    --region "${REGION}"
else
  echo "No RUNTIME_ARN provided; searching for runtime named: ${RUNTIME_NAME}"
  EXISTING_RUNTIME=$(aws bedrock-agentcore-control list-agent-runtimes \
    --region "${REGION}" \
    --query "agentRuntimes[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeId" \
    --output text || echo "")

  if [ -n "${EXISTING_RUNTIME}" ] && [ "${EXISTING_RUNTIME}" != "None" ]; then
    echo "Found existing runtime ID: ${EXISTING_RUNTIME}; updating"
    aws bedrock-agentcore-control update-agent-runtime \
      --agent-runtime-id "${EXISTING_RUNTIME}" \
      --cli-input-json file://agentcore-update.json \
      --region "${REGION}"
    RUNTIME_ARN=$(aws bedrock-agentcore-control get-agent-runtime \
      --agent-runtime-id "${EXISTING_RUNTIME}" \
      --region "${REGION}" \
      --query 'agentRuntimeArn' --output text)
  else
    echo "Creating new AgentCore runtime..."
    aws bedrock-agentcore-control create-agent-runtime \
      --cli-input-json file://agentcore-create.json \
      --region "${REGION}"
    RUNTIME_ID=$(aws bedrock-agentcore-control list-agent-runtimes \
      --region "${REGION}" \
      --query "agentRuntimes[?agentRuntimeName=='${RUNTIME_NAME}'].agentRuntimeId" \
      --output text)
    RUNTIME_ARN=$(aws bedrock-agentcore-control get-agent-runtime \
      --agent-runtime-id "${RUNTIME_ID}" \
      --region "${REGION}" \
      --query 'agentRuntimeArn' --output text)
  fi
fi

echo "Deployment completed successfully!"
echo "Runtime ARN: ${RUNTIME_ARN}"
echo "Update your environment configuration with:"
echo "AGENTCORE_RUNTIME_ARN=${RUNTIME_ARN}"

# Output to GitHub Actions step if available
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "runtime-arn=${RUNTIME_ARN}" >> "$GITHUB_OUTPUT"
fi

# Cleanup
rm -f agentcore-update.json agentcore-create.json