/**
 * Shared provider configuration utility for tests
 * Uses ConfigService to get actual provider configurations
 * Single source of truth: imports model constants from constants/models.ts
 */

import { ALL_MODELS, DEFAULT_MODELS } from '../constants/models';

export interface TestProviderConfig {
  name: string;
  tabName: RegExp;
  inputId: string;
  apiKey: string | null;
  preferredModels: readonly string[];
  defaultModel: string;
  badge: RegExp;
  type: 'api_key';
  hasCredentials: boolean;
  testPrompt: string; // For multi-provider testing
}

export type ProviderConfigs = {
  openai: TestProviderConfig;
  anthropic: TestProviderConfig;
  google: TestProviderConfig;
  aws_bedrock: TestProviderConfig;
};

/**
 * Get provider configurations using ConfigService
 * This ensures consistency with the actual application configuration
 */
export async function getProviderConfigs(): Promise<ProviderConfigs> {
  // For now, we'll use a simplified approach that reads from the same secrets
  // that ConfigService would use. In the future, this could directly import
  // and use ConfigService if we set up proper Node.js backend imports.
  
  const fs = await import('fs');
  const yaml = await import('js-yaml');
  const path = await import('path');
  
  interface SecretsConfig {
    llm_providers?: {
      openai?: { api_key?: string };
      anthropic?: { api_key?: string };
      gemini?: { api_key?: string };
      aws_bedrock?: { api_key?: string };
    };
    openai?: { api_key?: string };
    aws_bedrock?: { api_key?: string };
  }

  let secrets: SecretsConfig = {};
  try {
    const currentDir = path.dirname(new URL(import.meta.url).pathname);
    const secretsPath = path.join(currentDir, '../../../libs/common/secrets.yaml');
    const secretsContent = fs.readFileSync(secretsPath, 'utf8');
    secrets = yaml.load(secretsContent) as SecretsConfig;
  } catch (error) {
    console.warn("Could not load secrets.yaml:", error);
  }

  // Extract API keys using the same logic as ConfigService
  const openaiKey = secrets?.llm_providers?.openai?.api_key || secrets?.openai?.api_key;
  const anthropicKey = secrets?.llm_providers?.anthropic?.api_key;
  const geminiKey = secrets?.llm_providers?.gemini?.api_key;
  const awsBedrockKey = secrets?.llm_providers?.aws_bedrock?.api_key || secrets?.aws_bedrock?.api_key;

  return {
    openai: {
      name: 'OpenAI',
      tabName: /openai/i,
      inputId: 'openai-api-key',
      apiKey: openaiKey || null,
      preferredModels: ALL_MODELS.openai,
      defaultModel: DEFAULT_MODELS.openai,
      badge: /openai/i,
      type: 'api_key' as const,
      hasCredentials: !!openaiKey,
      testPrompt: "Hello! Please respond with exactly: 'OpenAI API connection successful'"
    },
    anthropic: {
      name: 'Anthropic',
      tabName: /anthropic/i,
      inputId: 'anthropic-api-key',
      apiKey: anthropicKey || null,
      preferredModels: ALL_MODELS.anthropic,
      defaultModel: DEFAULT_MODELS.anthropic,
      badge: /anthropic|claude/i,
      type: 'api_key' as const,
      hasCredentials: !!anthropicKey,
      testPrompt: "Hello! Please respond with exactly: 'Anthropic API connection successful'"
    },
    google: {
      name: 'Google',
      tabName: /google|gemini/i,
      inputId: 'google-api-key',
      apiKey: geminiKey || null,
      preferredModels: ALL_MODELS.google,
      defaultModel: DEFAULT_MODELS.google,
      badge: /google|gemini/i,
      type: 'api_key' as const,
      hasCredentials: !!geminiKey,
      testPrompt: "Hello! Please respond with exactly: 'Google API connection successful'"
    },
    aws_bedrock: {
      name: 'AWS Bedrock',
      tabName: /aws|bedrock/i,
      inputId: 'aws_bedrock-api-key',
      apiKey: awsBedrockKey || null,
      preferredModels: ALL_MODELS.aws_bedrock,
      defaultModel: DEFAULT_MODELS.aws_bedrock,
      badge: /aws|bedrock/i,
      type: 'api_key' as const,
      hasCredentials: !!awsBedrockKey,
      testPrompt: "Hello! Please respond with exactly: 'AWS Bedrock API connection successful'"
    }
  };
}

/**
 * Log available credentials for debugging
 */
export function logAvailableCredentials(configs: ProviderConfigs) {
  console.log('Available credentials:');
  Object.entries(configs).forEach(([, config]) => {
    console.log(`  ${config.name}: ${config.hasCredentials ? '✓' : '✗'} (API key)`);
  });
}
