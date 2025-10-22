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
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.small"  # ARM-based instance for cost efficiency
}

variable "ami_id" {
  description = "AMI ID for EC2 instances"
  type        = string
  default     = "ami-026fccd88446aa0bf"  # Ubuntu ARM AMI
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for EC2 access"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Cheapest option for dev
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "agent_league"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
}

variable "use_rds" {
  description = "Whether to use RDS or containerized PostgreSQL"
  type        = bool
  default     = false  # Default to containerized for cost savings
}

variable "enable_spot_instance" {
  description = "Whether to use spot instances for cost savings"
  type        = bool
  default     = true
}

variable "spot_price" {
  description = "Maximum spot price"
  type        = string
  default     = "0.05"  # Adjust based on current spot prices
}

variable "github_repository" {
  description = "GitHub repository in the format 'owner/repo'"
  type        = string
  default     = "iliagerman/agent_arena"  # Update this to match your repository
}


variable "pg_data_volume_size" {
  description = "Size of the EBS volume (GB) for PostgreSQL data"
  type        = number
  default     = 30
}
