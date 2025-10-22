variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "agentleague"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "hackathon"
}

variable "frontend_domain_name" {
  description = "Frontend domain name for CloudFront"
  type        = string
  default     = "app.hackathon.agentleague.ai"
}

variable "backend_domain_name" {
  description = "Backend API domain name for ALB"
  type        = string
  default     = "api.hackathon.agentleague.ai"
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate (wildcard for *.hackathon.agentleague.ai)"
  type        = string
  default     = "arn:aws:acm:us-east-1:619403130674:certificate/7f813be9-99f6-43dd-bce1-36a1c25f222e"
}

variable "aws_secrets_manager_secret_name" {
  description = "Name of the AWS Secrets Manager secret"
  type        = string
  default     = "hackathon_secret"
}

# DNS is managed in Cloudflare - no Route 53 zone needed
# ECR repositories are defined in ecr.tf

variable "ecr_agentcore_repository_url" {
  description = "ECR repository URL for agentcore"
  type        = string
  default     = "619403130674.dkr.ecr.us-east-1.amazonaws.com/agentleague-agentcore"
}

variable "backend_cpu" {
  description = "CPU units for backend ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "backend_memory" {
  description = "Memory for backend ECS task (in MB)"
  type        = number
  default     = 4096
}

variable "postgres_cpu" {
  description = "CPU units for PostgreSQL ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "postgres_memory" {
  description = "Memory for PostgreSQL ECS task (in MB)"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 1
}

variable "postgres_desired_count" {
  description = "Desired number of PostgreSQL tasks"
  type        = number
  default     = 1
}

variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100" # North America and Europe only
}

variable "s3_bucket_name" {
  description = "S3 bucket name for frontend static files"
  type        = string
  default     = "agentleague-hackathon-frontend"
}

# ============================================================================
# AURORA SERVERLESS V2 VARIABLES
# ============================================================================

variable "aurora_engine_version" {
  description = "Aurora PostgreSQL engine version"
  type        = string
  default     = "16.1" # Aurora PostgreSQL 16.1 supports Serverless v2
}

variable "aurora_database_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "agentleague"
}

variable "aurora_master_username" {
  description = "Master username for Aurora"
  type        = string
  default     = "postgres"
}

variable "aurora_min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity units (ACUs). 0.5 ACU = 1GB RAM"
  type        = number
  default     = 0.5 # Minimum for cost optimization
}

variable "aurora_max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity units (ACUs). 0.5 ACU = 1GB RAM"
  type        = number
  default     = 2 # Max 2 ACUs = 4GB RAM for hackathon
}

variable "aurora_backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
}
