#!/bin/bash

# Deployment script for EC2 instance
# This script should be placed on the EC2 instance at /opt/app/deploy.sh

set -e

# Configuration
PROJECT_NAME="agentleague"
AWS_REGION="us-east-1"
SECRETS_MANAGER_NAME="${PROJECT_NAME}-secrets"
COMPOSE_FILE="/opt/app/docker-compose.aws.yml"

echo "🚀 Starting deployment at $(date)"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    log "❌ This script must be run as root or with sudo"
    log "💡 Run with: sudo $0"
    exit 1
fi

# Get ECR repository URLs
log "📋 Getting ECR repository information..."
ECR_BACKEND_REPO=$(aws ecr describe-repositories --repository-names ${PROJECT_NAME}-backend --query 'repositories[0].repositoryUri' --output text --region $AWS_REGION)
ECR_FRONTEND_REPO=$(aws ecr describe-repositories --repository-names ${PROJECT_NAME}-frontend --query 'repositories[0].repositoryUri' --output text --region $AWS_REGION)

log "Backend repo: $ECR_BACKEND_REPO"
log "Frontend repo: $ECR_FRONTEND_REPO"

# Login to ECR
log "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_BACKEND_REPO

# Pull latest images
log "📥 Pulling latest images..."
docker pull $ECR_BACKEND_REPO:latest
docker pull $ECR_FRONTEND_REPO:latest

# Get secrets from AWS Secrets Manager
log "🔑 Retrieving secrets from AWS Secrets Manager..."
aws secretsmanager get-secret-value \
    --secret-id $SECRETS_MANAGER_NAME \
    --region $AWS_REGION \
    --query SecretString \
    --output text > /tmp/secrets.yaml

# Parse database password from secrets
DB_PASSWORD=$(python3 -c "
import yaml
with open('/tmp/secrets.yaml', 'r') as f:
    secrets = yaml.safe_load(f)
    print(secrets['database']['password'])
")

# Set environment variables for docker-compose
export ECR_BACKEND_REPO
export ECR_FRONTEND_REPO
export AWS_REGION
export SECRETS_MANAGER_NAME
export DB_NAME="agent_league"
export DB_USER="postgres"
export DB_PASSWORD
export DOMAIN_NAME="${DOMAIN_NAME:-localhost}"

# Create docker-compose.aws.yml if it doesn't exist
if [ ! -f "$COMPOSE_FILE" ]; then
    log "📝 Creating docker-compose.aws.yml..."
    cat > $COMPOSE_FILE << 'EOF'
version: '3.8'

services:
  backend:
    image: ${ECR_BACKEND_REPO}:latest
    container_name: agentleague-backend
    restart: unless-stopped
    environment:
      - APP_ENV=development
    ports:
      - "9998:9998"
    volumes:
      - app_logs:/app/logs
    depends_on:
      - db
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9998/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    image: ${ECR_FRONTEND_REPO}:latest
    container_name: agentleague-frontend
    restart: unless-stopped
    environment:
      - NODE_ENV=development
      - VITE_API_URL=
    ports:
      - "5888:5888"
    volumes:
      - app_logs:/app/logs
    depends_on:
      - backend
    networks:
      - app_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5888"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: pgvector/pgvector:pg17
    container_name: agentleague-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME:-agent_league}
      - POSTGRES_USER=${DB_USER:-postgres}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - app_logs:/var/log/postgresql
    networks:
      - app_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -d ${DB_NAME:-agent_league}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

volumes:
  postgres_data:
    driver: local
  app_logs:
    driver: local

networks:
  app_network:
    driver: bridge
EOF
fi

# Change to app directory
cd /opt/app

# Stop existing containers
log "🛑 Stopping existing containers..."
docker-compose -f docker-compose.aws.yml down || true

# Start new containers
log "🚀 Starting new containers..."
docker-compose -f docker-compose.aws.yml up -d

# Wait for services to be healthy
log "⏳ Waiting for services to start..."
sleep 30

# Check service health
log "🏥 Checking service health..."
docker-compose -f docker-compose.aws.yml ps

# Test endpoints
log "🧪 Testing endpoints..."
sleep 10

# Test backend
if curl -f http://localhost:9998/health > /dev/null 2>&1; then
    log "✅ Backend is healthy"
else
    log "⚠️  Backend health check failed"
fi

# Test frontend
if curl -f http://localhost:5888/ > /dev/null 2>&1; then
    log "✅ Frontend is healthy"
else
    log "⚠️  Frontend health check failed"
fi

# Clean up old images
log "🧹 Cleaning up old Docker images..."
docker image prune -f

log "✅ Deployment completed successfully at $(date)"

# Log container status
log "📊 Final container status:"
docker-compose -f docker-compose.aws.yml ps
