# Terraform variables for hackathon environment
# DNS is managed in Cloudflare

aws_region                      = "us-east-1"
project_name                    = "agentleague"
environment                     = "hackathon"
frontend_domain_name            = "app.hackathon.agentleague.ai"
backend_domain_name             = "api.hackathon.agentleague.ai"
certificate_arn                 = "arn:aws:acm:us-east-1:619403130674:certificate/7f813be9-99f6-43dd-bce1-36a1c25f222e"
aws_secrets_manager_secret_name = "hackathon_secret"

# ECR repositories are created in ecr.tf

# ECS configuration
backend_cpu           = 2048  # 2 vCPU
backend_memory        = 4096  # 4 GB
backend_desired_count = 1

# CloudFront configuration
cloudfront_price_class = "PriceClass_100" # North America and Europe

# S3 bucket
s3_bucket_name = "agentleague-hackathon-frontend"

# Aurora Serverless v2 configuration
aurora_engine_version           = "16.1"
aurora_database_name            = "agentleague"
aurora_master_username          = "postgres"
aurora_min_capacity             = 0.5  # 0.5 ACU = 1GB RAM
aurora_max_capacity             = 2    # 2 ACU = 4GB RAM
aurora_backup_retention_period  = 7

# AgentCore Runtime ARN will be created by Terraform and deployed via GitHub Actions

