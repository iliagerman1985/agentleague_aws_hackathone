# ============================================================================
# OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "backend_target_group_arn" {
  description = "Backend target group ARN"
  value       = aws_lb_target_group.backend.arn
}

output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "backend_service_name" {
  description = "Backend ECS service name"
  value       = aws_ecs_service.backend.name
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend"
  value       = aws_s3_bucket.frontend.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for frontend"
  value       = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://${var.frontend_domain_name}"
}

output "backend_url" {
  description = "Backend API URL"
  value       = "https://${var.backend_domain_name}"
}

output "game_turn_queue_url" {
  description = "Game turn SQS queue URL"
  value       = aws_sqs_queue.game_turn.url
}

output "game_analysis_queue_url" {
  description = "Game analysis SQS queue URL"
  value       = aws_sqs_queue.game_analysis.url
}

# ============================================================================
# AURORA RDS OUTPUTS
# ============================================================================

output "aurora_cluster_id" {
  description = "Aurora cluster ID"
  value       = aws_rds_cluster.aurora.id
}

output "aurora_cluster_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.aurora.endpoint
}

output "aurora_cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.aurora.reader_endpoint
}

output "aurora_cluster_port" {
  description = "Aurora cluster port"
  value       = aws_rds_cluster.aurora.port
}

output "aurora_database_name" {
  description = "Aurora database name"
  value       = aws_rds_cluster.aurora.database_name
}

output "aurora_master_username" {
  description = "Aurora master username"
  value       = aws_rds_cluster.aurora.master_username
  sensitive   = true
}

output "aurora_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Aurora credentials"
  value       = aws_secretsmanager_secret.aurora_credentials.arn
}

output "database_connection_string" {
  description = "Database connection string (without password)"
  value       = "postgresql://${aws_rds_cluster.aurora.master_username}@${aws_rds_cluster.aurora.endpoint}:${aws_rds_cluster.aurora.port}/${aws_rds_cluster.aurora.database_name}"
  sensitive   = true
}

# ============================================================================
# AGENTCORE OUTPUTS
# ============================================================================

output "agentcore_runtime_role_arn" {
  description = "ARN of the IAM role for AgentCore runtime execution"
  value       = aws_iam_role.agentcore_runtime.arn
}

output "agentcore_runtime_role_name" {
  description = "Name of the IAM role for AgentCore runtime execution"
  value       = aws_iam_role.agentcore_runtime.name
}

output "agentcore_log_group_name" {
  description = "Name of the CloudWatch log group for AgentCore"
  value       = aws_cloudwatch_log_group.agentcore.name
}

# ============================================================================
# ECR OUTPUTS
# ============================================================================

output "ecr_backend_repository_url" {
  description = "ECR repository URL for backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_backend_repository_name" {
  description = "ECR repository name for backend"
  value       = aws_ecr_repository.backend.name
}

output "ecr_agentcore_repository_url" {
  description = "ECR repository URL for AgentCore"
  value       = aws_ecr_repository.agentcore.repository_url
}

output "ecr_agentcore_repository_name" {
  description = "ECR repository name for AgentCore"
  value       = aws_ecr_repository.agentcore.name
}
