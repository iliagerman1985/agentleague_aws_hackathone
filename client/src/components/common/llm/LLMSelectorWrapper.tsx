import React from 'react';
import { EnhancedLLMModelSelector } from '@/components/llm/EnhancedLLMModelSelector';
import { useLLMSelection, LLMSelectionContext } from '@/hooks/useLLMSelection';

interface LLMSelectorWrapperProps {
  context?: LLMSelectionContext;
  compact?: boolean;
  label?: string;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  showSettings?: boolean;
}

/**
 * LLMSelectorWrapper provides a simplified interface to EnhancedLLMModelSelector
 * with consistent context-aware state management and persistence
 */
export const LLMSelectorWrapper: React.FC<LLMSelectorWrapperProps> = ({
  context = 'global',
  compact = false,
  label,
  placeholder,
  className,
  disabled = false,
  showSettings = true
}) => {
  const { selectedModel, setSelectedModel } = useLLMSelection({ context });



  return (
    <EnhancedLLMModelSelector
      selectedModel={selectedModel}
      onSelectionChange={setSelectedModel}
      className={className}
      compact={compact}
      label={label}
      placeholder={placeholder}
      disabled={disabled}
      showSettings={showSettings}
    />
  );
};

export default LLMSelectorWrapper;
