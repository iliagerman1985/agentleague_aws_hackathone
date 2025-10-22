import React, { useState, useEffect, useCallback } from "react";
import { SharedModal } from "@/components/common/SharedModal";
import { DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToasts } from "@/components/common/notifications/ToastProvider";
import { LLMProviderCard } from "./LLMProviderCard";
import { ConfirmDialog } from "@/components/common/dialogs/ConfirmDialog";
import { useAuth } from "@/contexts/AuthContext";

import { api, LLMProvider, LLMIntegrationResponse, ProviderModels } from "@/lib/api";
import { type LLMIntegrationId } from "@/types/ids";

interface LLMIntegrationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onIntegrationChange?: () => void; // Callback when integrations are modified
}

export const LLMIntegrationDialog: React.FC<LLMIntegrationDialogProps> = ({
  open,
  onOpenChange,
  onIntegrationChange
}) => {
  const [integrations, setIntegrations] = useState<LLMIntegrationResponse[]>([]);
  const [availableModels, setAvailableModels] = useState<ProviderModels>({});
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<LLMProvider>(LLMProvider.OPENAI);
  const [modifiedProviders, setModifiedProviders] = useState<Set<LLMProvider>>(new Set());
  const [pendingSaveData, setPendingSaveData] = useState<Record<LLMProvider, any>>({} as Record<LLMProvider, any>);
  const [showConfirmClose, setShowConfirmClose] = useState(false);
  const { push } = useToasts();
  const { user } = useAuth();
  
  const isAdmin = user?.role === 'admin';

  const loadData = async () => {
    setLoading(true);
    try {
      const [integrationsData, modelsData] = await Promise.all([
        api.llmIntegrations.list(),
        api.llmIntegrations.getAvailableModels()
      ]);
      setIntegrations(integrationsData);

      // Transform the new API format to the expected format
      console.log('Available models received:', modelsData);
      if (Array.isArray(modelsData)) {
        // New format: array of LLMProviderModels
        const transformedModels: ProviderModels = {};
        modelsData.forEach((providerData: any) => {
          transformedModels[providerData.provider] = {
            models: providerData.models.map((model: any) => model.model_id)
          };
        });
        console.log('Available models transformed:', transformedModels);
        setAvailableModels(transformedModels);
      } else {
        // Old format: already in the expected shape
        setAvailableModels(modelsData);
      }
    } catch (error) {
      console.error('Error loading LLM integrations:', error);

      // Extract error message from the error object
      let errorMessage = "Failed to load LLM integrations";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      push({
        title: "Error",
        message: errorMessage,
        tone: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  // Load integrations and available models when dialog opens
  useEffect(() => {
    if (open) {
      loadData();
      setModifiedProviders(new Set());
      setPendingSaveData({} as Record<LLMProvider, any>);
    }
  }, [open]); // Removed loadData from dependencies to prevent infinite loop



  const handleSave = useCallback(async (data: {
    provider: LLMProvider;
    apiKey: string;
    selectedModel: string;
    displayName?: string;
  }) => {
    console.log('Storing pending save data for:', data.provider);
    setPendingSaveData(prev => ({ ...prev, [data.provider]: data }));
    setModifiedProviders(prev => new Set(prev).add(data.provider));
  }, []);

  const handleDirtyStateChange = useCallback((provider: LLMProvider, isDirty: boolean) => {
    if (!isDirty) {
      setModifiedProviders(prev => {
        const newSet = new Set(prev);
        newSet.delete(provider);
        return newSet;
      });
    }
  }, []);

  const hasModifications = modifiedProviders.size > 0;

  const handleOkClick = async () => {
    if (hasModifications) {
      await saveAllChanges();
    }
    onOpenChange(false);
  };

  const handleDialogClose = (open: boolean) => {
    if (!open && hasModifications) {
      setShowConfirmClose(true);
    } else {
      onOpenChange(open);
    }
  };

  const saveAllChanges = async () => {
    setLoading(true);
    try {
      for (const provider of modifiedProviders) {
        const data = pendingSaveData[provider];
        if (!data) continue;

        console.log('Saving integration for provider:', provider, data);

        const existingIntegration = integrations.find(i => i.provider === provider);
        const action = existingIntegration ? 'update' : 'create';

        // Non-admins can't create or update API keys
        if (!isAdmin) {
          console.log(`Skipping ${provider} - user is not admin`);
          continue;
        }

        // Validation: API key is required for new integrations
        if (action === 'create' && !data.apiKey) {
          console.log(`Skipping ${provider} - API key required for new integration`);
          continue;
        }

        if (action === 'update' && existingIntegration) {
          const updateData: any = {
            selected_model: data.selectedModel,
            display_name: data.displayName,
          };

          // Only include API key if provided (for updates, it's optional)
          if (data.apiKey) {
            updateData.api_key = data.apiKey;
          }

          console.log('Updating integration:', existingIntegration.id, updateData);
          await api.llmIntegrations.update(existingIntegration.id, updateData);
        } else {
          const createData: any = {
            provider: provider,
            api_key: data.apiKey,
            selected_model: data.selectedModel,
            is_active: true,
            is_default: integrations.length === 0,
          };

          if (data.displayName && data.displayName.trim()) {
            createData.display_name = data.displayName.trim();
          }

          console.log('Creating integration:', createData);
          await api.llmIntegrations.create(createData);
        }

        push({
          title: "Success",
          message: `${provider} integration ${action === 'create' ? 'created' : 'updated'} successfully`,
          tone: "success",
        });
      }

      // Reset states after successful save
      setModifiedProviders(new Set());
      setPendingSaveData({} as Record<LLMProvider, any>);

      // Reload data and notify parent
      await loadData();
      onIntegrationChange?.();

    } catch (error) {
      console.error('Error saving integrations:', error);

      let errorMessage = "Failed to save integrations";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      push({
        title: "Error",
        message: errorMessage,
        tone: "error",
      });
    } finally {
      setLoading(false);
    }
  };


  const handleDelete = async (integrationId: LLMIntegrationId) => {
    setLoading(true);
    try {
      await api.llmIntegrations.delete(integrationId);
      push({
        title: "Success",
        message: "Integration deleted successfully",
        tone: "success",
      });
      // Reload data to update the UI after deletion
      await loadData();
      onIntegrationChange?.();
    } catch (error) {
      console.error('Error deleting integration:', error);

      // Extract error message from the error object
      let errorMessage = "Failed to delete integration";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      push({
        title: "Error",
        message: errorMessage,
        tone: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (args: { provider: LLMProvider; integrationId?: LLMIntegrationId; apiKey?: string; model?: string; }) => {
    setLoading(true);
    try {
      if (args.integrationId) {
        await api.llmIntegrations.setDefault(args.integrationId);
      } else {
        if (!args.apiKey || !args.model) {
          throw new Error("API key and model are required to create a default integration");
        }
        await api.llmIntegrations.create({
          provider: args.provider,
          apiKey: args.apiKey,
          selectedModel: args.model,
          isActive: true,
          isDefault: true,
        });
      }
      push({ title: "Success", message: "Default provider updated", tone: "success" });
      await loadData();
      onIntegrationChange?.();
    } catch (error) {
      let errorMessage = "Failed to set default integration";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      push({ title: "Error", message: errorMessage, tone: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleTestWithApiKey = async (provider: LLMProvider, apiKey: string, model: string) => {
    try {
      const result = await api.llmIntegrations.testApiKey({
        provider: provider,
        api_key: apiKey,
        model: model,
        test_prompt: "Hello, please respond with 'API connection successful'"
      });
      return result;
    } catch (error) {
      return {
        success: false,
        error_message: error instanceof Error ? error.message : "Test failed"
      };
    }
  };



  const getIntegrationForProvider = (provider: LLMProvider) => {
    return integrations.find(i => i.provider === provider);
  };

  const getModelsForProvider = (provider: LLMProvider): string[] => {
    return availableModels[provider]?.models || [];
  };

  return (
    <>
      <SharedModal open={open} onOpenChange={handleDialogClose} title="🤖 LLM Integrations" description="Configure your API keys and select models for different LLM providers. Your API keys are encrypted and stored securely." size="xl" className="sm:max-w-4xl max-h-[90vh] overflow-y-auto p-0">

          <div className="px-6 pt-6 pb-4">
            <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as LLMProvider)} className="w-full">
              <TabsList className="grid w-full grid-cols-4 focus-visible:ring-0 focus-visible:ring-offset-0">
                <TabsTrigger value={LLMProvider.OPENAI}>OpenAI</TabsTrigger>
                <TabsTrigger value={LLMProvider.ANTHROPIC}>Anthropic</TabsTrigger>
                <TabsTrigger value={LLMProvider.GOOGLE}>Google</TabsTrigger>
                <TabsTrigger value={LLMProvider.AWS_BEDROCK}>AWS Bedrock</TabsTrigger>
              </TabsList>

              {Object.values(LLMProvider).map((provider) => (
                <TabsContent key={provider} value={provider} className="mt-6">
                <LLMProviderCard
                  provider={provider}
                  integration={getIntegrationForProvider(provider)}
                  availableModels={getModelsForProvider(provider)}
                  onSave={handleSave}
                  onDelete={handleDelete}
                  onTestWithApiKey={handleTestWithApiKey}
                  onDirtyStateChange={(isDirty) => handleDirtyStateChange(provider, isDirty)}
                  onCancel={() => onOpenChange(false)}
                  loading={loading}
                  hideButtons={true}
                  hasPendingChanges={modifiedProviders.has(provider)}
                  onSetDefault={handleSetDefault}
                  isAdmin={isAdmin}
                />
              </TabsContent>
            ))}
            </Tabs>
          </div>

          <DialogFooter className="px-6 py-4 border-t">
            <div className="flex items-center gap-2 w-full">
              <Button
                variant="outline"
                onClick={() => handleDialogClose(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleOkClick}
                disabled={loading}
                className="ml-auto"
                data-testid="llm-dialog-ok"
              >
                OK
              </Button>
            </div>
          </DialogFooter>
      </SharedModal>

      <ConfirmDialog
        open={showConfirmClose}
        onOpenChange={setShowConfirmClose}
        title="Unsaved Changes"
        description="You have unsaved changes. Are you sure you want to close without saving?"
        confirmText="Close Without Saving"
        cancelText="Cancel"
        onConfirm={() => {
          setShowConfirmClose(false);
          onOpenChange(false);
        }}
      />
    </>
  );
};

export default LLMIntegrationDialog;
