# ============================================================================
# NOTE: Service Discovery removed - Aurora RDS uses direct endpoint
# Database endpoint is available via aws_rds_cluster.aurora.endpoint
# ============================================================================

# ============================================================================
# SQS QUEUES
# ============================================================================

# Game Turn Queue
resource "aws_sqs_queue" "game_turn" {
  name                       = "agentleague-game-turn-queue-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

  tags = {
    Name        = "${var.project_name}-${var.environment}-game-turn-queue"
    Environment = var.environment
  }
}

# Game Turn Dead Letter Queue
resource "aws_sqs_queue" "game_turn_dlq" {
  name                       = "agentleague-game-turn-queue-${var.environment}-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

  tags = {
    Name        = "${var.project_name}-${var.environment}-game-turn-dlq"
    Environment = var.environment
  }
}

# Redrive policy for Game Turn Queue
resource "aws_sqs_queue_redrive_policy" "game_turn" {
  queue_url = aws_sqs_queue.game_turn.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.game_turn_dlq.arn
    maxReceiveCount     = 3
  })
}

# Game Analysis Queue
resource "aws_sqs_queue" "game_analysis" {
  name                       = "agentleague-game-analysis-queue-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

  tags = {
    Name        = "${var.project_name}-${var.environment}-game-analysis-queue"
    Environment = var.environment
  }
}

# Game Analysis Dead Letter Queue
resource "aws_sqs_queue" "game_analysis_dlq" {
  name                       = "agentleague-game-analysis-queue-${var.environment}-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

  tags = {
    Name        = "${var.project_name}-${var.environment}-game-analysis-dlq"
    Environment = var.environment
  }
}

# Redrive policy for Game Analysis Queue
resource "aws_sqs_queue_redrive_policy" "game_analysis" {
  queue_url = aws_sqs_queue.game_analysis.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.game_analysis_dlq.arn
    maxReceiveCount     = 3
  })
}

# ============================================================================
# DNS RECORDS - MANAGED IN CLOUDFLARE
# ============================================================================
# DNS is managed in Cloudflare, not Route 53
# After terraform apply, create these records in Cloudflare:
#
# Frontend (app.hackathon.agentleague.ai):
#   Type: CNAME
#   Name: app.hackathon
#   Target: <cloudfront_distribution_domain_name> (from terraform output)
#   Proxy: Enabled (orange cloud)
#
# Backend (api.hackathon.agentleague.ai):
#   Type: CNAME
#   Name: api.hackathon
#   Target: <alb_dns_name> (from terraform output)
#   Proxy: Disabled (gray cloud) - Required for ALB health checks
# ============================================================================
