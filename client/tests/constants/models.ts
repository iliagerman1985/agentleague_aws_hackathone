/**
 * Model constants for testing
 * Re-exports from the shared constants file to maintain backward compatibility
 * Single source of truth: client/src/constants/models.ts
 */

export {
  OpenAIModel,
  AnthropicModel,
  GoogleModel,
  AWSBedrockModel,
  PROVIDER_MODELS,
  DEFAULT_MODELS,
  ALL_MODELS,
  type OpenAIModelType,
  type AnthropicModelType,
  type GoogleModelType,
  type AWSBedrockModelType
} from '../../src/constants/models';
