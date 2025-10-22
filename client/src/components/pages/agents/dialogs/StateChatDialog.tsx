import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import VibeChat, { type ChatMessage } from '@/components/tools/VibeChat';
import { LLMSelectorWrapper } from '@/components/common/llm/LLMSelectorWrapper';
import { useAgentLLM } from '@/contexts/LLMContext';
import { type AgentId } from '@/types/ids';
import { streamStateChat, type StateChatMessage, fetchStateChatExamples } from '@/services/stateChatService';
import { Button } from '@/components/ui/button';
import CodeEditor from '@/components/tools/CodeEditor';

import { SharedModal } from '@/components/common/SharedModal';

import { agentsService, GameEnvironment } from '@/services/agentsService';
import { GameStatePreview } from '@/components/games/GameStatePreview';
import { useToasts } from '@/components/common/notifications/ToastProvider';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: AgentId | null;
  environment?: GameEnvironment | null; // Optional: if provided, used instead of fetching from agent
  initialState?: Record<string, any> | null;
  initialDescription?: string | null;
  onApply: (state: Record<string, any>, description: string) => void | Promise<void>;
  modificationMode?: boolean; // When true, only allow modifying existing state (not generating from scratch)
  onShowLLMDialog?: () => void; // Optional: callback to show LLM integration dialog
}

export const StateChatDialog: React.FC<Props> = ({
  open,
  onOpenChange,
  agentId,
  environment: providedEnvironment,
  initialState = null,
  initialDescription = '',
  onApply,
  modificationMode = false,
  onShowLLMDialog
}) => {
  // Use the same model selection state as the Tool Editor (agents context)
  const { selectedModel } = useAgentLLM();
  const { push } = useToasts();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [draftState, setDraftState] = useState<string>(() => JSON.stringify(initialState ?? {}, null, 2));
  const [description, setDescription] = useState<string>(String(initialDescription ?? ''));
  const [lastFinalState, setLastFinalState] = useState<Record<string, any> | null>(initialState ?? null);
  const [statePreviewOpen, setStatePreviewOpen] = useState(false);
  const [hasGenerated, setHasGenerated] = useState(false);

  const [applying, setApplying] = useState(false);
  const [environment, setEnvironment] = useState<GameEnvironment | null>(providedEnvironment ?? null);


  // Seed initial description into chat when dialog opens
  useEffect(() => {
    if (open && initialDescription && messages.length === 0) {
      setMessages([{ id: crypto.randomUUID(), role: 'assistant', text: String(initialDescription) }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Load agent environment to render visual state preview inline in chat
  // If environment is provided directly, use it; otherwise fetch from agent
  useEffect(() => {
    if (!open) return;

    // If environment is provided directly, use it
    if (providedEnvironment) {
      setEnvironment(providedEnvironment);
      return;
    }

    // Otherwise, fetch from agent
    if (!agentId) return;
    let cancelled = false;
    (async () => {
      try {
        const a = await agentsService.get(agentId);
        if (!cancelled) setEnvironment(a?.gameEnvironment ?? null);
      } catch {
        if (!cancelled) setEnvironment(null);
      }
    })();
    return () => { cancelled = true; };
  }, [open, agentId, providedEnvironment]);

  // Environment-provided example prompts (fetched per agent)
  const [examplePrompts, setExamplePrompts] = useState<string[]>([]);
  useEffect(() => {
    if (!open || !agentId) return;
    fetchStateChatExamples(String(agentId)).then((prompts) => {
      // In modification mode, filter out prompts that suggest generating from scratch
      if (modificationMode) {
        const modificationPrompts = prompts.filter(p =>
          !p.toLowerCase().includes('create') &&
          !p.toLowerCase().includes('generate') &&
          !p.toLowerCase().includes('new position')
        );
        setExamplePrompts(modificationPrompts);
      } else {
        setExamplePrompts(prompts);
      }
    }).catch(() => setExamplePrompts([]));
  }, [open, agentId, modificationMode]);

  const conversationHistory = useMemo<StateChatMessage[]>(() => (
    messages.map(m => ({ writer: m.role === 'user' ? 'human' : 'llm', content: m.text }))
  ), [messages]);

  const parseJSON = useCallback((text: string): Record<string, any> | null => {
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }, []);

  const appendMessage = useCallback((msg: ChatMessage) => setMessages(prev => [...prev, msg]), []);
  const updateAssistantText = useCallback((id: string, more: string) => setMessages(prev => prev.map(m => m.id === id ? { ...m, text: m.text + (more || '') } : m)), []);
	  const replaceMessageText = useCallback((id: string, text: string) =>
	    setMessages(prev => prev.map(m => (m.id === id ? { ...m, text } : m))),
	  []);


  const onSend = useCallback(async (text: string): Promise<boolean> => {
    // Check if LLM integration is selected
    if (!selectedModel?.integrationId) {
      push({
        title: "No LLM Model Selected",
        message: "Please add an LLM integration to continue.",
        tone: "error",
      });
      // Open LLM integration dialog
      if (onShowLLMDialog) {
        onShowLLMDialog();
      }
      return false;
    }

    // Check if environment is available (required for state generation)
    if (!environment) {
      push({
        title: "Environment Not Available",
        message: "Please select a game environment to generate states.",
        tone: "error",
      });
      return false;
    }

    // Validate JSON input (if provided)
    const currentStateObj = draftState.trim() ? parseJSON(draftState) : null;
    if (draftState.trim() && !currentStateObj) return false; // Block if invalid

    const userId = crypto.randomUUID();
    appendMessage({ id: userId, role: 'user', text });

    const asstId = crypto.randomUUID();
    appendMessage({ id: asstId, role: 'assistant', text: '' });
    setIsTyping(true);

    // Debug: starting stream
    // Use system chess agent if no agentId provided and environment is chess
    const SYSTEM_CHESS_AGENT_ID = '760453725797653372';
    const effectiveAgentId = agentId || (environment === GameEnvironment.CHESS ? SYSTEM_CHESS_AGENT_ID : null);

    if (!effectiveAgentId) {
      push({
        title: "Configuration Error",
        message: "Unable to determine agent for state generation.",
        tone: "error",
      });
      return false;
    }

    console.debug('[StateChat] start', {
      agentId: String(effectiveAgentId),
      model: selectedModel?.integrationId,
      hasCurrentState: !!(draftState.trim()),
    });

      // Hoisted so finally can access them
      let assistantAccum = "";

      // Encourage richer, user-friendly description from the model
      const augmentedText = `${text}\n\nPlease also include a detailed, user-friendly Description (3–6 sentences) summarizing positions, stacks, blinds, pot, community cards, and action so far. Ensure the Description exactly matches the final JSON state.`;

    try {
      for await (const chunk of streamStateChat(String(effectiveAgentId), {
        message: augmentedText,
        conversation_history: conversationHistory,
        llm_integration_id: selectedModel.integrationId,
        model_id: selectedModel.modelId,
        current_state: currentStateObj,
      })) {
        if ((chunk as any).type === 'content') {
          const c = (chunk as any).content || '';
          assistantAccum += c;
          // Debug: content chunk length
          if (c) console.debug('[StateChat] content chunk', { len: c.length });
          updateAssistantText(asstId, c);
        } else if ((chunk as any).type === 'done') {
          const final = (chunk as any).final as any;
          console.debug('[StateChat] done chunk received', final);
          const nextMessage: string = final?.message || '';
          const nextDescription: string = final?.description || '';
          const nextState: Record<string, any> | null = final?.state ?? null;

          console.debug('[StateChat] parsed payload', { hasDesc: !!nextDescription, hasMsg: !!nextMessage, stateKeys: nextState ? Object.keys(nextState).length : 0 });
          // Update description and state
          setDescription(nextDescription || '');
          setDraftState(JSON.stringify(nextState ?? {}, null, 2));
          setLastFinalState(nextState ?? {});
          setHasGenerated(true);
          // Replace the streamed assistant message with the final description (per UX decision)
          replaceMessageText(asstId, nextDescription || assistantAccum);
          console.debug('[StateChat] UI updated');
        } else if ((chunk as any).type === 'error') {
          const errorMsg = (chunk as any).error ?? 'Unknown error';

          // Check if error is about LLM integration and open dialog (same pattern as ToolEditorPage)
          const lowerError = errorMsg.toLowerCase();
          if (lowerError.includes('provider or integration unavailable') ||
              lowerError.includes('llm integration not found') ||
              lowerError.includes('integration not found') ||
              lowerError.includes('access denied')) {
            if (onShowLLMDialog) {
              onShowLLMDialog();
            }
            // Don't show the error message - just open the dialog
          } else {
            // Show error message for other types of errors
            updateAssistantText(asstId, `\n[Error] ${errorMsg}`);
          }
        }
      }
    } catch (error) {
      console.error('[StateChat] error', error);
      const message = error instanceof Error ? error.message : String(error ?? 'Unknown error');
      const lowerMsg = message.toLowerCase();

      // Check if error is about LLM integration and open dialog
      if (lowerMsg.includes('provider or integration unavailable') ||
          lowerMsg.includes('llm integration not found') ||
          lowerMsg.includes('integration not found') ||
          lowerMsg.includes('access denied')) {
        if (onShowLLMDialog) {
          onShowLLMDialog();
        }
        // Don't show the error message - just open the dialog
      } else {
        // Show error message for other types of errors
        updateAssistantText(asstId, `\n[Error] ${message}`);
      }
    } finally {
      setIsTyping(false);
    }
    return true;
  }, [agentId, environment, appendMessage, conversationHistory, draftState, parseJSON, selectedModel?.integrationId, updateAssistantText, push, onShowLLMDialog]);

  const canApply = !!lastFinalState && typeof description === 'string' && description.length >= 0;

  const onClearChat = useCallback(() => {
    setMessages([]);
    setDescription('');
    // Clear the board/state preview as well
    setDraftState(JSON.stringify({}, null, 2));
    setLastFinalState(null);
    setHasGenerated(false);
    setStatePreviewOpen(false);
  }, []);

  const onClose = () => {
    // reset minimal state on close
    setIsTyping(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl w-[96vw] h-[96vh] p-0 overflow-y-auto overflow-x-hidden" style={{ width: 'min(96vw, 72rem)' }}>
        <div className="flex flex-col h-full pb-20 md:pb-24 min-w-0 max-w-full overflow-hidden">
        <DialogHeader className="px-4 pt-3 pb-2">
          <DialogTitle>{modificationMode ? 'Modify State' : 'State Chat (Generate or Edit)'}</DialogTitle>
          <DialogDescription>
            {modificationMode
              ? 'Describe how you want to modify the current state. The assistant will update the state based on your instructions.'
              : 'Chat to generate a new state or edit the current one. The assistant will rewrite the description to match the state.'
            }
          </DialogDescription>
        </DialogHeader>
        {/* Model selector (compact dropdown to match Tool Editor) - only render when dialog is open */}
        {open && (
          <div className="px-4 py-2 flex justify-center">
            <LLMSelectorWrapper
              context="agents"
              compact={true}
              placeholder="Select a model"
              showSettings={true}
            />
          </div>
        )}


        {/* Content area - single column with chat and collapsible state */}
        <div className="flex flex-col flex-1 min-h-0 min-w-0">
          <VibeChat
            messages={messages}
            onSend={onSend}
            isTyping={isTyping}
            onClearAll={onClearChat}
            hideModelSelector
            llmContext="agents"
            headerTransparent
            className="flex-1 min-h-0 min-w-0 w-full !h-full !m-0 rounded-xl no-card-hover"
            inputPlaceholder={modificationMode
              ? "Describe how to modify the current state... (Shift+Enter for new line)"
              : "Ask me to generate or edit the game state... (Shift+Enter for new line)"
            }
            quickPrompts={examplePrompts}
            quickPromptsPlacement="above"
            emptyTitle={modificationMode ? "Hi! I'm your State Modifier." : "Hi! I'm your State Generator."}
            emptySubtitle={modificationMode
              ? "Describe how you want to change the current state."
              : "Describe the situation or ask to modify the current state."
            }
            autoScroll={true}
            onShowLLMDialog={onShowLLMDialog}
            extraBelowMessages={hasGenerated ? (
              <div className="w-full flex flex-col items-center gap-2">
                {environment && (
                  <div className="w-full max-w-3xl rounded-lg border bg-card p-2" data-testid="state-preview-embedded">
                    <GameStatePreview environment={environment} jsonText={draftState} />
                  </div>
                )}
                <Button
                  variant="default"
                  onClick={() => setStatePreviewOpen(true)}
                  className="text-sm px-4 py-2.5 h-auto font-medium"
                  data-testid="state-preview-json-button"
                >
                  Show State JSON
                </Button>
              </div>
            ) : undefined}

          />
        </div>
        <div className="sticky bottom-0 w-full bg-transparent backdrop-blur-0 border-t-0 px-4 py-1 md:py-2 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            disabled={!canApply || applying}
            onClick={async () => {
              if (!lastFinalState) return;
              setApplying(true);
              try {
                await Promise.resolve(onApply(lastFinalState, description || ''));
                onOpenChange(false);
              } finally {
                setApplying(false);
              }
            }}
          >
            {applying ? 'Applying…' : 'Apply State'}
          </Button>
        </div>

          {hasGenerated && (
            <SharedModal
              open={statePreviewOpen}
              onOpenChange={setStatePreviewOpen}
              title="Generated State"
              description="This is the latest generated game state (read-only)."
              size="xl"
              className="w-[92vw]"
              footer={lastFinalState ? (
                <Button
                  variant="outline"
                  onClick={() => navigator.clipboard.writeText(JSON.stringify(lastFinalState ?? {}, null, 2))}
                  data-testid="state-preview-copy-json"
                >
                  Copy JSON
                </Button>
              ) : undefined}
            >
              <CodeEditor
                value={JSON.stringify(lastFinalState ?? {}, null, 2)}
                language="text"
                onChange={() => {}}
                readOnly
                height="60vh"
              />
            </SharedModal>
          )}

        </div>
      </DialogContent>
    </Dialog>
  );
};

export default StateChatDialog;

