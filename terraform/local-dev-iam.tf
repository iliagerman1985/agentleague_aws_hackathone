# IAM Policy for Local Development User
# This policy grants necessary permissions for local development and testing

resource "aws_iam_policy" "local_dev_agentcore" {
  name        = "${var.project_name}-local-dev-agentcore-policy"
  description = "Policy for local development user to access AgentCore and related services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:DeleteAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:ListAgentRuntimes"
        ]
        Resource = [
          "*",
          "arn:aws:bedrock-agentcore:${var.aws_region}:*:runtime/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:dev_secret*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = [
          aws_sqs_queue.process_message.arn,
          aws_sqs_queue.process_message_dead_letter.arn,
          aws_sqs_queue.billing_events.arn,
          aws_sqs_queue.webhooks.arn,
          aws_sqs_queue.game_turn.arn,
          aws_sqs_queue.game_turn_dead_letter.arn,
          aws_sqs_queue.game_analysis.arn,
          aws_sqs_queue.game_analysis_dead_letter.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Purpose     = "local-development"
  }
}

# Attach the policy to the local development user
resource "aws_iam_user_policy_attachment" "local_dev_agentcore_attachment" {
  user       = "local_test_dany"
  policy_arn = aws_iam_policy.local_dev_agentcore.arn
}