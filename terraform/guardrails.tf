# AWS Bedrock Guardrails Configuration
# This file defines guardrails for content validation in the AgentLeague application

# Guardrail for Agent Instructions Validation
resource "aws_bedrock_guardrail" "agent_instructions" {
  name        = "${var.project_name}-agent-instructions-${var.environment}"
  description = "Validates agent instructions for harmful content and prompt attacks"

  blocked_input_messaging  = "Your agent instructions contain content that violates our policies. Please revise and try again."
  blocked_outputs_messaging = "The content was blocked due to policy violations."

  # Content filters for harmful content
  content_policy_config {
    filters_config {
      type           = "HATE"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "INSULTS"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "SEXUAL"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "VIOLENCE"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "MISCONDUCT"
      input_strength = "MEDIUM"
      output_strength = "NONE"
    }

    # Prompt attack filter REMOVED for agent instructions
    # Agent instructions need to allow coaching phrases like "you are the best"
    # which trigger false positives even at LOW sensitivity
  }

  tags = {
    Name        = "${var.project_name}-agent-instructions-${var.environment}"
    Environment = var.environment
    Purpose     = "agent-validation"
  }
}

# Create a version of the guardrail for production use
resource "aws_bedrock_guardrail_version" "agent_instructions_v1" {
  guardrail_arn = aws_bedrock_guardrail.agent_instructions.guardrail_arn
  description   = "Version 1 - Initial release"
}

# Version 2 with updated PROMPT_ATTACK filter (LOW sensitivity)
resource "aws_bedrock_guardrail_version" "agent_instructions_v2" {
  guardrail_arn = aws_bedrock_guardrail.agent_instructions.guardrail_arn
  description   = "Version 2 - Reduced PROMPT_ATTACK sensitivity to LOW to allow legitimate coaching phrases"

  depends_on = [aws_bedrock_guardrail.agent_instructions]
}

# Version 3 with PROMPT_ATTACK filter completely removed
resource "aws_bedrock_guardrail_version" "agent_instructions_v3" {
  guardrail_arn = aws_bedrock_guardrail.agent_instructions.guardrail_arn
  description   = "Version 3 - Removed PROMPT_ATTACK filter to allow all coaching phrases while keeping other safety filters"

  depends_on = [aws_bedrock_guardrail.agent_instructions]
}

# Guardrail for Tool Creation Chat Validation
resource "aws_bedrock_guardrail" "tool_creation_chat" {
  name        = "${var.project_name}-tool-creation-${var.environment}"
  description = "Validates tool creation chat for on-topic conversations and harmful content"

  blocked_input_messaging  = "Your message violates our usage policies. Please keep conversations focused on tool creation for your game environment."
  blocked_outputs_messaging = "The response was blocked due to policy violations."

  # Content filters
  content_policy_config {
    filters_config {
      type           = "HATE"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "INSULTS"
      input_strength = "MEDIUM"
      output_strength = "NONE"
    }

    filters_config {
      type           = "SEXUAL"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "VIOLENCE"
      input_strength = "HIGH"
      output_strength = "NONE"
    }

    filters_config {
      type           = "MISCONDUCT"
      input_strength = "MEDIUM"
      output_strength = "NONE"
    }

    filters_config {
      type           = "PROMPT_ATTACK"
      input_strength = "HIGH"
      output_strength = "NONE"
    }
  }

  # Denied topics for off-topic conversations
  topic_policy_config {
    topics_config {
      name       = "OffTopicConversations"
      definition = "Requests unrelated to game tool creation or test generation, including general knowledge, trivia, casual chat, and personal questions."
      type       = "DENY"

      examples = [
        "Tell me a joke",
        "How many stars in the universe?",
        "What's the weather like?",
        "Help me write an essay"
      ]
    }

    topics_config {
      name       = "UnrelatedTechnicalRequests"
      definition = "Technical requests unrelated to game tools or tests, such as web development, mobile apps, or general programming outside tool creation context."
      type       = "DENY"

      examples = [
        "Help me build a website",
        "How do I create a mobile app?",
        "Write a Python script to scrape websites"
      ]
    }

    topics_config {
      name       = "GeneralProgrammingHelp"
      definition = "General programming questions or tutorials not specifically about implementing game environment tools or test scenarios."
      type       = "DENY"

      examples = [
        "Explain object-oriented programming",
        "What are design patterns?",
        "Teach me Python basics"
      ]
    }
  }

  tags = {
    Name        = "${var.project_name}-tool-creation-${var.environment}"
    Environment = var.environment
    Purpose     = "tool-creation-validation"
  }
}

# Create a version for production use
resource "aws_bedrock_guardrail_version" "tool_creation_v1" {
  guardrail_arn = aws_bedrock_guardrail.tool_creation_chat.guardrail_arn
  description   = "Version 1 - Initial release"
}

# IAM policy for Bedrock Guardrails
resource "aws_iam_policy" "bedrock_guardrails" {
  name        = "${var.project_name}-bedrock-guardrails-${var.environment}"
  description = "Policy for accessing Bedrock Guardrails"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:ApplyGuardrail",
          "bedrock:GetGuardrail",
          "bedrock:ListGuardrails"
        ]
        Resource = [
          aws_bedrock_guardrail.agent_instructions.guardrail_arn,
          aws_bedrock_guardrail.tool_creation_chat.guardrail_arn,
          "${aws_bedrock_guardrail.agent_instructions.guardrail_arn}/*",
          "${aws_bedrock_guardrail.tool_creation_chat.guardrail_arn}/*"
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-bedrock-guardrails-${var.environment}"
    Environment = var.environment
  }
}

# Attach guardrails policy to EC2 instance role
resource "aws_iam_role_policy_attachment" "ec2_guardrails" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.bedrock_guardrails.arn
}

# Outputs for use in application
output "guardrail_agent_instructions_id" {
  description = "ID of the agent instructions guardrail"
  value       = aws_bedrock_guardrail.agent_instructions.guardrail_id
}

output "guardrail_agent_instructions_version" {
  description = "Version of the agent instructions guardrail (latest)"
  value       = aws_bedrock_guardrail_version.agent_instructions_v3.version
}

output "guardrail_agent_instructions_version_v1" {
  description = "Version 1 of the agent instructions guardrail (deprecated - HIGH sensitivity)"
  value       = aws_bedrock_guardrail_version.agent_instructions_v1.version
}

output "guardrail_agent_instructions_version_v2" {
  description = "Version 2 of the agent instructions guardrail (deprecated - LOW sensitivity)"
  value       = aws_bedrock_guardrail_version.agent_instructions_v2.version
}

output "guardrail_tool_creation_id" {
  description = "ID of the tool creation guardrail"
  value       = aws_bedrock_guardrail.tool_creation_chat.guardrail_id
}

output "guardrail_tool_creation_version" {
  description = "Version of the tool creation guardrail"
  value       = aws_bedrock_guardrail_version.tool_creation_v1.version
}

