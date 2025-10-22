/**
 * Model constants - single source of truth for LLM model names
 * These should match the enums in libs/shared_db/shared_db/models/llm_enums.py
 */

export const OpenAIModel = {
  GPT_5_MINI: "gpt-5-mini",      // Fast
  GPT_5: "gpt-5"                 // Slow
} as const;

export const AnthropicModel = {
  CLAUDE_HAIKU_35: "claude-haiku-4-5-20251001-v1:0",      // Fast
  CLAUDE_SONNET_4: "claude-sonnet-4-5-20250929-v1:0"       // Slow
} as const;

export const GoogleModel = {
  GEMINI_2_5_FLASH: "gemini-2.5-flash",    // Fast
  GEMINI_2_5_PRO: "gemini-2.5-pro"         // Slow
} as const;

export const AWSBedrockModel = {
  AWS_CLAUDE_HAIKU_35: "us.anthropic.claude-haiku-4-5-20251001-v1:0",    // Fast
  AWS_CLAUDE_SONNET_4: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"     // Slow
} as const;

// Type definitions
export type OpenAIModelType = typeof OpenAIModel[keyof typeof OpenAIModel];
export type AnthropicModelType = typeof AnthropicModel[keyof typeof AnthropicModel];
export type GoogleModelType = typeof GoogleModel[keyof typeof GoogleModel];
export type AWSBedrockModelType = typeof AWSBedrockModel[keyof typeof AWSBedrockModel];

// Provider model mappings
export const PROVIDER_MODELS = {
  openai: OpenAIModel,
  anthropic: AnthropicModel,
  google: GoogleModel,
  aws_bedrock: AWSBedrockModel
} as const;

// Default models (fast models as default)
export const DEFAULT_MODELS = {
  openai: OpenAIModel.GPT_5_MINI,
  anthropic: AnthropicModel.CLAUDE_HAIKU_35,
  google: GoogleModel.GEMINI_2_5_FLASH,
  aws_bedrock: AWSBedrockModel.AWS_CLAUDE_HAIKU_35
} as const;

// All models for each provider (ordered by preference: fast first, then slow)
export const ALL_MODELS = {
  openai: [OpenAIModel.GPT_5_MINI, OpenAIModel.GPT_5],
  anthropic: [AnthropicModel.CLAUDE_HAIKU_35, AnthropicModel.CLAUDE_SONNET_4],
  google: [GoogleModel.GEMINI_2_5_FLASH, GoogleModel.GEMINI_2_5_PRO],
  aws_bedrock: [AWSBedrockModel.AWS_CLAUDE_HAIKU_35, AWSBedrockModel.AWS_CLAUDE_SONNET_4]
} as const;

