# Terraform configuration for AgentLeague dev environment
# Generated configuration with your specific settings

# AWS Configuration
aws_region = "us-east-1"

# Project Configuration
project_name = "agentleague"
environment  = "dev"

# EC2 Configuration
instance_type        = "t4g.small"  # ARM-based instance for cost efficiency
ami_id              = "ami-026fccd88446aa0bf"  # Ubuntu 22.04 ARM64
key_pair_name       = "dev"  # Your key pair name (corresponds to dev.pem)
enable_spot_instance = false
spot_price          = "0.05"  # Adjusted spot price for ARM instances

# Domain and SSL
domain_name     = "app.dev.agentleague.app"  # Your application domain
certificate_arn = "arn:aws:acm:us-east-1:619403130674:certificate/b0e6efd5-1c57-42a8-9deb-b29ab04eef56"  # Your ACM certificate ARN

# GitHub Configuration (for OIDC authentication)
github_repository = "iliagerman/agent_arena"  # Your GitHub repository

# Database Configuration
use_rds              = false  # Use containerized PostgreSQL for cost savings
db_instance_class    = "db.t3.micro"  # Only used if use_rds = true
db_allocated_storage = 20
db_name             = "agent_league"
db_username         = "postgres"
