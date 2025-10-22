import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

import { Eye, EyeOff, FlaskConical, Trash2 } from "lucide-react";
import { LLMProvider, LLMIntegrationResponse } from "@/lib/api";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { ProviderIcon } from "@/components/llm/ProviderIcon";
import { type LLMIntegrationId } from "@/types/ids";
import { DEFAULT_MODELS } from "@/constants/models";

interface LLMTestResult {
  success: boolean;
  response_text?: string;
  error_message?: string;
  latency_ms?: number;
}

interface LLMProviderCardProps {
  provider: LLMProvider;
  integration?: LLMIntegrationResponse;
  availableModels: string[];
  onSave?: (data: { provider: LLMProvider; apiKey: string; selectedModel: string; displayName?: string }) => Promise<void>;
  onDelete?: (integrationId: LLMIntegrationId) => Promise<void>;
  onTestWithApiKey?: (provider: LLMProvider, apiKey: string, model: string) => Promise<LLMTestResult>;
  onDirtyStateChange?: (isDirty: boolean) => void;
  onCancel?: () => void;
  loading?: boolean;
  hideButtons?: boolean;
  hasPendingChanges?: boolean;
  onSetDefault?: (args: { provider: LLMProvider; integrationId?: LLMIntegrationId; apiKey?: string; model?: string }) => Promise<void>;
  isAdmin?: boolean;
}

const PROVIDER_INFO = {
  [LLMProvider.OPENAI]: {
    name: "OpenAI",
    description: "GPT models including GPT-5 Mini (fast) and GPT-5 (advanced)",
    color: "bg-brand-orange/10 text-brand-orange border-brand-orange/20",
    docUrl: "https://platform.openai.com/docs/api-reference"
  },
  [LLMProvider.ANTHROPIC]: {
    name: "Anthropic",
    description: "Claude models for advanced reasoning and analysis",
    color: "bg-brand-orange/10 text-brand-orange border-brand-orange/20",
    docUrl: "https://docs.anthropic.com/claude/reference/getting-started-with-the-api"
  },
  [LLMProvider.GOOGLE]: {
    name: "Google",
    description: "Gemini models for multimodal AI capabilities",
    color: "bg-brand-purple/10 text-brand-purple border-brand-purple/20",
    docUrl: "https://ai.google.dev/docs"
  },
  [LLMProvider.AWS_BEDROCK]: {
    name: "AWS Bedrock",
    description: "Claude, models via AWS Bedrock",
    color: "bg-brand-cyan/10 text-brand-cyan border-brand-cyan/20",
    docUrl: "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html"
  }
};

export const LLMProviderCard: React.FC<LLMProviderCardProps> = ({
  provider,
  integration,
  availableModels,
  onSave,
  onDelete,
  onTestWithApiKey,
  onDirtyStateChange,
  loading = false,
  hasPendingChanges = false,
  onSetDefault,
  isAdmin = false,
}) => {

  // Function to get current form data for external save


  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'openai': return 'OpenAI';
      case 'anthropic': return 'Anthropic';
      case 'google': return 'Google';
      case 'aws_bedrock': return 'AWS Bedrock';
      default: return provider;
    }
  };

  const getDefaultModel = () => {
    if (integration?.selectedModel) return integration.selectedModel;

    // Prefer server-provided list if available
    if (availableModels.length > 0) return availableModels[0];

    // Fallback defaults (fast models) - use constants from single source of truth
    return DEFAULT_MODELS[provider as keyof typeof DEFAULT_MODELS] || "";
  };

  const [showApiKey, setShowApiKey] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [settingDefault, setSettingDefault] = useState(false);
  const [testResult, setTestResult] = useState<(LLMTestResult & { testing?: boolean }) | null>(null);
  const [initialFormData, setInitialFormData] = useState({
    apiKey: "",
    selectedModel: getDefaultModel()
  });

  const [formData, setFormData] = useState({
    apiKey: "",
    selectedModel: getDefaultModel()
  });
  const onSaveRef = useRef(onSave);
  const onDirtyRef = useRef(onDirtyStateChange);
  useEffect(() => { onSaveRef.current = onSave; }, [onSave]);
  useEffect(() => { onDirtyRef.current = onDirtyStateChange; }, [onDirtyStateChange]);


  const providerInfo = PROVIDER_INFO[provider];

  // Initialize form data when integration changes
  useEffect(() => {
    const newFormData = {
      apiKey: "",
      selectedModel: getDefaultModel()
    };
    setFormData(newFormData);
    setInitialFormData(newFormData);
  }, [integration, provider, availableModels]);

  // Check if form is dirty and notify parent, and auto-save changes
  useEffect(() => {
    const isDirty = formData.apiKey !== initialFormData.apiKey ||
                   formData.selectedModel !== initialFormData.selectedModel;
    onDirtyRef.current?.(isDirty);

    // Auto-save when form changes
    if (isDirty) {
      const saveData = {
        provider,
        apiKey: formData.apiKey,
        selectedModel: formData.selectedModel,
        displayName: undefined
      };
      console.log('Auto-saving changes:', { ...saveData, apiKey: formData.apiKey ? '***' : '' });
      onSaveRef.current?.(saveData);
    }
  }, [formData, initialFormData, provider]);



  const handleTestWithFormData = async () => {
    if (!onTestWithApiKey) return;

    // Validation - API key is required
    if (!formData.apiKey) return;

    setTestResult({ success: false, testing: true });

    try {
      const result = await onTestWithApiKey(provider, formData.apiKey, getDefaultModel());
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        error_message: error instanceof Error ? error.message : "Test failed",
        testing: false
      });
    }
  };

  const handleSetDefault = async () => {
    if (!onSetDefault) return;
    setSettingDefault(true);
    try {
      await onSetDefault({
        provider,
        integrationId: integration?.id,
        apiKey: !integration ? formData.apiKey : undefined,
        model: !integration ? getDefaultModel() : undefined,
      });
    } finally {
      setSettingDefault(false);
    }
  };

  return (
    <Card className="w-full no-card-hover">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <ProviderIcon provider={provider} size={20} className="h-5 w-5" />
              {providerInfo.name}
            </CardTitle>
            {integration?.isDefault && (
              <Badge variant="secondary">Default</Badge>
            )}
            {hasPendingChanges && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                Pending Changes
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {integration && (
              <Badge className={(integration.isActive ? "bg-primary/15 text-primary border-primary/20" : "bg-muted-foreground/15 text-muted-foreground border-muted-foreground/20") + " border"}>
                {integration.isActive ? "Active" : "Inactive"}
              </Badge>
            )}
            {((integration && !integration.isDefault) || (!integration && !!formData.apiKey && isAdmin)) && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleSetDefault}
                disabled={loading || settingDefault || (!integration && !formData.apiKey)}
                className="h-8"
              >
                {settingDefault ? "Setting..." : "Set as Default"}
              </Button>
            )}
            {integration && onDelete && isAdmin && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={loading}
                className="h-9 w-9 p-0"
                aria-label="Delete integration"
                data-testid="llm-delete-integration"
              >
                <Trash2 className="h-6 w-6" />
              </Button>
            )}
          </div>
        </div>
        <CardDescription>
          {providerInfo.description}
          {" • "}
          <a
            href={providerInfo.docUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-teal hover:text-brand-cyan dark:text-brand-teal dark:hover:text-brand-cyan"
          >
            API Documentation
          </a>
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Always show the editing form */}
        {true && (
          <>
            {/* Standard API key field - only for admins */}
            {isAdmin && (
              <div className="space-y-2">
                {/* Do not log real API key values in UI logs */}
                <Label htmlFor={`${provider}-api-key`}>API Key</Label>
                <div className="relative">
                  <Input
                    id={`${provider}-api-key`}
                    type={showApiKey ? "text" : "password"}
                    value={formData.apiKey}
                    onChange={(e) => {
                      setFormData(prev => ({ ...prev, apiKey: e.target.value }));
                      setTestResult(null); // Clear test result when API key changes
                    }}
                    placeholder={integration ? "Enter new API key (leave empty to keep current)" : "Enter your API key"}
                    data-adornment-end="true"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowApiKey(!showApiKey)}
                  >
                    {showApiKey ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </Button>
                </div>
              </div>
            )}

            {/* For non-admin users, show integration exists but is managed by admin */}
            {!isAdmin && integration && (
              <div className="space-y-2">
                <Label>API Integration</Label>
                <p className="text-sm text-muted-foreground">
                  This integration is managed by system administrators. You can set it as your default provider.
                </p>
              </div>
            )}

            {/* For non-admin users without integration */}
            {!isAdmin && !integration && (
              <div className="space-y-2">
                <Label>API Integration</Label>
                <p className="text-sm text-muted-foreground">
                  No integration available for this provider. Contact an administrator.
                </p>
              </div>
            )}

            {/* Test button - only for admins */}
            {isAdmin && (
              <div className="pt-2">
                <Button
                  variant="outline"
                  onClick={handleTestWithFormData}
                  disabled={loading || testResult?.testing || !formData.apiKey}
                  className="w-full flex items-center gap-2"
                >
                  <FlaskConical className="h-4 w-4" />
                  {testResult?.testing ? "Testing..." : "Test"}
                </Button>
              </div>
            )}

            {/* Test Result Display */}
            {testResult && !testResult.testing && (
              <div className={`mt-3 p-3 rounded-lg border ${
                testResult.success
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : 'bg-red-50 border-red-200 text-red-800'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  {testResult.success ? (
                    <>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-sm">Success</span>
                      {testResult.latency_ms && (
                        <span className="text-xs opacity-75">({testResult.latency_ms}ms)</span>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      <span className="font-medium text-sm">Failed</span>
                    </>
                  )}
                </div>
                <div className="text-sm">
                  {testResult.success
                    ? testResult.response_text || "API connection successful"
                    : testResult.error_message || "Test failed"
                  }
                </div>
              </div>
            )}

            {/* Save/Cancel buttons are now handled by the parent dialog */}
          </>
        )}
      </CardContent>

      {/* Delete Confirmation Dialog */}
      {integration && (
        <ConfirmDialog
          open={showDeleteConfirm}
          onOpenChange={setShowDeleteConfirm}
          title="Delete Integration"
          description={`Are you sure you want to delete the ${getProviderName(integration.provider)} integration? This action cannot be undone.`}
          confirmText="Delete"
          cancelText="Cancel"
          onConfirm={() => onDelete?.(integration.id)}
        />
      )}
    </Card>
  );
};

export default LLMProviderCard;
