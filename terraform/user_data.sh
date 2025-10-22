#!/bin/bash

# User data script for EC2 instance setup (Ubuntu ARM)
# This script installs Docker, configures logging, and sets up auto-deployment

set -e

# Variables from Terraform
PROJECT_NAME="${project_name}"
AWS_REGION="${aws_region}"
ECR_BACKEND_REPO="${ecr_backend_repo}"
ECR_FRONTEND_REPO="${ecr_frontend_repo}"
ECR_AGENTCORE_REPO="${ecr_agentcore_repo}"
SECRETS_MANAGER_NAME="${secrets_manager_name}"
LOG_GROUP_APP="${log_group_app}"
LOG_GROUP_BACKEND="${log_group_backend}"
LOG_GROUP_FRONTEND="${log_group_frontend}"
LOG_GROUP_POSTGRES="${log_group_postgres}"
LOG_GROUP_AGENTCORE="${log_group_agentcore}"

ENVIRONMENT="${environment}"
# Update system
apt-get update -y
apt-get upgrade -y

# Install required packages
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    unzip \
    python3 \
    python3-pip \
    python3-yaml

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io
systemctl start docker
systemctl enable docker
usermod -a -G docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install AWS CLI v2 for ARM64
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install CloudWatch agent for Ubuntu ARM64
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/arm64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb
rm -f amazon-cloudwatch-agent.deb

# Attach and mount EBS volume for PostgreSQL data
set +e
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
VOLUME_ID=$(aws ec2 describe-volumes --region "$AWS_REGION" \
  --filters "Name=tag:Name,Values=$${PROJECT_NAME}-pg-data" "Name=availability-zone,Values=$AZ" \
  --query 'Volumes[0].VolumeId' --output text)

if [ "$VOLUME_ID" != "None" ] && [ -n "$VOLUME_ID" ]; then
  ATTACHED_INSTANCE=$(aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$VOLUME_ID" --query 'Volumes[0].Attachments[0].InstanceId' --output text 2>/dev/null || echo "")
  if [ -n "$ATTACHED_INSTANCE" ] && [ "$ATTACHED_INSTANCE" != "None" ] && [ "$ATTACHED_INSTANCE" != "$INSTANCE_ID" ]; then
    aws ec2 detach-volume --region "$AWS_REGION" --volume-id "$VOLUME_ID" || true
    sleep 10
  fi

  aws ec2 attach-volume --region "$AWS_REGION" --volume-id "$VOLUME_ID" --instance-id "$INSTANCE_ID" --device /dev/xvdf || true
  # Wait for device to appear
  sleep 10

  DEV_PATH="/dev/nvme1n1"
  if [ ! -b "$DEV_PATH" ]; then
    DEV_PATH="/dev/xvdf"
  fi

  mkdir -p /mnt/pgdata
  # Make filesystem if missing
  if ! blkid "$DEV_PATH" >/dev/null 2>&1; then
    mkfs -t ext4 -F "$DEV_PATH"
  fi

  # Mount persistently via fstab
  UUID=$(blkid -s UUID -o value "$DEV_PATH")
  if ! grep -q "$UUID" /etc/fstab; then
    echo "UUID=$UUID /mnt/pgdata ext4 defaults,nofail 0 2" >> /etc/fstab
  fi

  mount -a || mount "$DEV_PATH" /mnt/pgdata
fi
set -e

# Create application directory
mkdir -p /opt/app
cd /opt/app

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/app/logs/app.log",
                        "log_group_name": "$LOG_GROUP_APP",
                        "log_stream_name": "{instance_id}/$ENVIRONMENT/app",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/app/logs/backend.log",
                        "log_group_name": "$LOG_GROUP_BACKEND",
                        "log_stream_name": "{instance_id}/$ENVIRONMENT/backend",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/app/logs/frontend.log",
                        "log_group_name": "$LOG_GROUP_FRONTEND",
                        "log_stream_name": "{instance_id}/$ENVIRONMENT/frontend",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/app/logs/postgres.log",
                        "log_group_name": "$LOG_GROUP_POSTGRES",
                        "log_stream_name": "{instance_id}/$ENVIRONMENT/postgres",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "AWS/EC2/Custom",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Create logs directory
mkdir -p /opt/app/logs

# Create deployment script
cat > /opt/app/deploy.sh << EOF
#!/bin/bash

set -e

PROJECT_NAME="$PROJECT_NAME"
AWS_REGION="$AWS_REGION"
ECR_BACKEND_REPO="$ECR_BACKEND_REPO"
ECR_FRONTEND_REPO="$ECR_FRONTEND_REPO"
ECR_AGENTCORE_REPO="$ECR_AGENTCORE_REPO"
SECRETS_MANAGER_NAME="$SECRETS_MANAGER_NAME"

echo "Starting deployment at $(date)"

# Stop and remove any existing containers to avoid conflicts
echo "Stopping and removing existing containers..."
CONTAINERS=$(docker ps -aq 2>/dev/null || true)
if [ -n "$CONTAINERS" ]; then
    echo "Found containers to clean up: $CONTAINERS"
    docker stop $CONTAINERS 2>/dev/null || true
    docker rm $CONTAINERS 2>/dev/null || true
    echo "Containers cleaned up successfully"
else
    echo "No containers found to clean up"
fi

# Quick cleanup before deployment (preserve PostgreSQL data)
echo "Running cleanup..."
docker system prune -af || true  # No --volumes to preserve PostgreSQL data
find /opt/app/logs -name "*.gz" -mtime +2 -delete 2>/dev/null || true
find /opt/app/logs -name "*.zip" -mtime +2 -delete 2>/dev/null || true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_BACKEND_REPO

# Pull latest images
echo "Pulling latest images..."
docker pull $ECR_BACKEND_REPO:latest || echo "Backend image not found, will build locally"
docker pull $ECR_FRONTEND_REPO:latest || echo "Frontend image not found, will build locally"

# Get secrets from AWS Secrets Manager (create empty file if secret doesn't exist)
echo "Retrieving secrets from AWS Secrets Manager..."
if aws secretsmanager get-secret-value --secret-id $SECRETS_MANAGER_NAME --region $AWS_REGION --query SecretString --output text > /tmp/secrets.yaml 2>/dev/null; then
    echo "Secrets retrieved successfully"
else
    echo "Warning: Secrets not found in AWS Secrets Manager, creating empty secrets file"
    echo "# Empty secrets file - configure secrets in AWS Secrets Manager" > /tmp/secrets.yaml
fi

# Start new containers
echo "Starting new containers..."

# Try to find docker-compose.aws.yml in multiple locations
COMPOSE_FILE=""
if [ -f "/opt/app/docker-compose.aws.yml" ]; then
    COMPOSE_FILE="/opt/app/docker-compose.aws.yml"
    cd /opt/app
elif [ -f "/home/ubuntu/docker-compose.aws.yml" ]; then
    COMPOSE_FILE="/home/ubuntu/docker-compose.aws.yml"
    cd /home/ubuntu
else
    echo "Error: docker-compose.aws.yml not found in /opt/app or /home/ubuntu"
    echo "Contents of /opt/app:"
    ls -la /opt/app/ || true
    echo "Contents of /home/ubuntu:"
    ls -la /home/ubuntu/ || true
    exit 1
fi

echo "Using docker-compose file: $COMPOSE_FILE"

# Always stop existing containers first using docker-compose
echo "Stopping existing containers with docker-compose..."
# Use project name to ensure consistent container naming
PROJECT_NAME="agentleague"
docker-compose -p $PROJECT_NAME -f docker-compose.aws.yml down 2>/dev/null || true

# Also try from different directories to catch orphaned containers
cd /opt/app 2>/dev/null && docker-compose -p $PROJECT_NAME -f docker-compose.aws.yml down 2>/dev/null || true
cd /home/ubuntu 2>/dev/null && docker-compose -p $PROJECT_NAME -f docker-compose.aws.yml down 2>/dev/null || true

# Start new containers with consistent project name
echo "Starting containers with docker-compose..."
docker-compose -p $PROJECT_NAME -f docker-compose.aws.yml up -d

echo "Deployment completed at $(date)"
EOF

chmod +x /opt/app/deploy.sh

# Create docker-compose.aws.yml file
cat > /opt/app/docker-compose.aws.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  backend:
    image: $${ECR_BACKEND_REPO}:latest
    container_name: agentleague-backend
    restart: unless-stopped
    environment:
      - APP_ENV=development
    ports:
      - "9998:9998"
    volumes:
      - /opt/app/logs:/app/logs
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
    image: $${ECR_FRONTEND_REPO}:latest
    container_name: agentleague-frontend
    restart: unless-stopped
    environment:
      - NODE_ENV=development
      - VITE_API_URL=
    ports:
      - "5888:5888"
    volumes:
      - /opt/app/logs:/app/logs
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
      - POSTGRES_DB=$${DB_NAME:-agent_league}
      - POSTGRES_USER=$${DB_USER:-postgres}
      - POSTGRES_PASSWORD=$${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - /mnt/pgdata:/var/lib/postgresql/data
      - app_logs:/var/log/postgresql
    networks:
      - app_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${DB_USER:-postgres} -d $${DB_NAME:-agent_league}"]
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
COMPOSE_EOF

# Create systemd service for auto-deployment
cat > /etc/systemd/system/app-deploy.service << EOF
[Unit]
Description=Application Deployment Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/app
ExecStart=/opt/app/deploy.sh
User=root

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer for periodic deployment checks
cat > /etc/systemd/system/app-deploy.timer << EOF
[Unit]
Description=Check for application updates every 5 minutes
Requires=app-deploy.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Auto-deploy disabled; CI pipeline will start containers
# systemctl daemon-reload
# systemctl enable app-deploy.timer
# systemctl start app-deploy.timer

# Webhook removed - using SSH-based deployment from GitHub Actions

echo "EC2 instance setup completed at $(date)" >> /var/log/user-data.log
