output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "security_group_alb_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "security_group_ec2_id" {
  description = "ID of the EC2 security group"
  value       = aws_security_group.ec2.id
}

output "ecr_backend_repository_url" {
  description = "URL of the backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecr_agentcore_repository_url" {
  description = "URL of the AgentCore ECR repository"
  value       = aws_ecr_repository.agentcore.repository_url
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret (managed by scripts)"
  value       = "dev_secret"
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret (managed by scripts)"
  value       = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:dev_secret"
}

output "cloudwatch_log_group_names" {
  description = "Names of the CloudWatch log groups"
  value = {
    app      = aws_cloudwatch_log_group.app_logs.name
    backend  = aws_cloudwatch_log_group.backend_logs.name
    frontend = aws_cloudwatch_log_group.frontend_logs.name
    postgres = aws_cloudwatch_log_group.postgres_logs.name
    agentcore = aws_cloudwatch_log_group.agentcore_logs.name
  }
}

output "sqs_queue_urls" {
  description = "URLs of the SQS queues"
  value = {
    process_message             = aws_sqs_queue.process_message.url
    process_message_dead_letter = aws_sqs_queue.process_message_dead_letter.url
    billing_events              = aws_sqs_queue.billing_events.url
    webhooks                    = aws_sqs_queue.webhooks.url
    game_turn                   = aws_sqs_queue.game_turn.url
    game_turn_dead_letter       = aws_sqs_queue.game_turn_dead_letter.url
  }
}

output "sqs_queue_arns" {
  description = "ARNs of the SQS queues"
  value = {
    process_message             = aws_sqs_queue.process_message.arn
    process_message_dead_letter = aws_sqs_queue.process_message_dead_letter.arn
    billing_events              = aws_sqs_queue.billing_events.arn
    webhooks                    = aws_sqs_queue.webhooks.arn
    game_turn                   = aws_sqs_queue.game_turn.arn
    game_turn_dead_letter       = aws_sqs_queue.game_turn_dead_letter.arn
  }
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer - Point your Cloudflare DNS to this"
  value       = aws_lb.main.dns_name
}

output "application_url" {
  description = "URL where the application should be accessible"
  value       = "https://${var.domain_name}"
}
