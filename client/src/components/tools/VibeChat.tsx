import React, { useEffect, useRef, useState } from "react";
import { LoadingDots } from "@/components/magicui/LoadingDots";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { LLMSelectorWrapper } from "@/components/common";
import { ModelSelection } from "@/lib/api";
import { useLLMSelection, type LLMSelectionContext } from "@/hooks/useLLMSelection";
import { Sparkles, Trash2 } from "lucide-react";
import { MessageContent } from "./MessageContent";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  replyTo?: string; // ID of message being replied to
}

interface VibeChatProps {
  messages: ChatMessage[];
  onSend: (text: string, replyTo?: string, selectedModel?: ModelSelection) => Promise<boolean> | boolean;
  isTyping?: boolean;
  className?: string;
  quickPrompts?: string[];
  onClearAll?: () => void;
  hideHeader?: boolean;
  headerTransparent?: boolean; // When true, header has no background
  onUseCode?: (code: string) => void;
  hideModelSelector?: boolean;
  inputPlaceholder?: string;
  quickPromptsPlacement?: "above" | "below";
  constrainedLayout?: boolean; // New prop for the special layout
  emptyTitle?: string;
  emptySubtitle?: string;
  onTestJsonGenerated?: (json: string) => void; // New callback for when test JSON is generated
  onShowLLMDialog?: () => void; // Callback to show LLM integration dialog
  llmContext?: LLMSelectionContext; // NEW: which LLM context to use (default 'tools')
  autoScroll?: boolean;
  extraBelowMessages?: React.ReactNode; // Custom content rendered inside chat area below messages
  onTestButtonClick?: () => boolean; // Custom handler for Test button - return true to prevent default behavior
}

export const VibeChat: React.FC<VibeChatProps> = ({ messages, onSend, isTyping = false, className, quickPrompts = ["Test", "Explain"], onClearAll, hideHeader = false, headerTransparent = false, onUseCode, hideModelSelector = false, inputPlaceholder, quickPromptsPlacement = "below", constrainedLayout = false, emptyTitle, emptySubtitle, onTestJsonGenerated, onShowLLMDialog, llmContext = "tools", autoScroll = true, extraBelowMessages, onTestButtonClick }) => {
  const [draft, setDraft] = useState("");
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { selectedModel } = useLLMSelection({ context: llmContext });
  const [waitingForTestJson, setWaitingForTestJson] = useState(false);

  const inputRef = useRef<HTMLDivElement | null>(null);
  const [bottomPad, setBottomPad] = useState<number>(0);

  // Smart auto-scroll state
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesBeforeStreaming = useRef(messages.length);

  useEffect(() => {
    const updatePad = () => {
      const h = inputRef.current ? inputRef.current.offsetHeight : 0;
      // Small extra gap for breathing room
      setBottomPad(h + 8);
    };
    updatePad();
    window.addEventListener("resize", updatePad);
    return () => window.removeEventListener("resize", updatePad);
  }, [draft, replyingTo, quickPrompts.length]);

  // Detect streaming state changes
  useEffect(() => {
    const wasStreaming = isStreaming;
    const nowStreaming = isTyping;

    if (nowStreaming && !wasStreaming) {
      // Started streaming - track message count and reset scroll state
      messagesBeforeStreaming.current = messages.length;
      setIsStreaming(true);
      setIsUserScrolledUp(false);
    } else if (!nowStreaming && wasStreaming) {
      // Finished streaming - reset state so next message will auto-scroll
      setIsStreaming(false);
      setIsUserScrolledUp(false);
    }
  }, [isTyping, messages.length]);

  // Reset scroll state when new messages arrive (user or assistant)
  useEffect(() => {
    // When a new message is added, reset the scroll-up flag so auto-scroll works
    setIsUserScrolledUp(false);
  }, [messages.length]);

  // Handle scroll events to detect user scroll up
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    let scrollTimeout: NodeJS.Timeout | null = null;

    const handleScroll = () => {
      // Clear any pending timeout
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      // Debounce to avoid false positives from programmatic scrolls
      scrollTimeout = setTimeout(() => {
        const { scrollTop, scrollHeight, clientHeight } = container;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

        // Only mark as scrolled up if significantly away from bottom (more than 150px)
        // This prevents programmatic smooth scrolls from triggering the flag
        if (distanceFromBottom > 150) {
          setIsUserScrolledUp(true);
        }
      }, 200); // Longer debounce to let smooth scroll finish
    };

    container.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      if (scrollTimeout) clearTimeout(scrollTimeout);
      container.removeEventListener("scroll", handleScroll);
    };
  }, []);


  useEffect(() => {
    if (!autoScroll) return;

    // Only auto-scroll if:
    // 1. User hasn't scrolled up during streaming, OR
    // 2. We're not currently streaming (new messages)
    const shouldAutoScroll = !isUserScrolledUp || !isStreaming;

    if (shouldAutoScroll) {
      // Use requestAnimationFrame to ensure DOM has updated and layout is complete
      requestAnimationFrame(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }
  }, [messages, isTyping, autoScroll, isUserScrolledUp, isStreaming]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [draft]);

  return (
    <div className={`flex w-full min-w-0 max-w-full overflow-hidden flex-col bg-transparent ${constrainedLayout ? 'max-h-[70vh] m-4 mb-6 rounded-xl' : 'h-full'} ${className ?? ""}`}>
      {/* Header */}
      {!hideHeader && (
        <div className={`${headerTransparent ? 'bg-transparent text-foreground' : 'bg-slate-800 text-white'} px-4 py-3 flex items-center justify-between gap-3 ${constrainedLayout ? 'rounded-t-xl' : ''}`}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2">
              <div className="font-medium text-base">AI Tool Assistant</div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">Online</span>
            </div>
          </div>
          {onClearAll && (
            <Button
              onClick={onClearAll}
              variant="ghost"
              size="sm"
              className="text-sm"
              data-testid="clear-chat"
            >
              <Trash2 className="h-4 w-4 sm:hidden" />
              <span className="hidden sm:inline">Clear chat</span>
            </Button>
          )}
        </div>
      )}

      {/* LLM Model Selector */}
      {!hideModelSelector && (
        <div className="px-2 sm:px-4 py-3">
          <LLMSelectorWrapper
            context={llmContext}
            compact={true}
            placeholder="Select a model"
            className="border-none"
          />
        </div>
      )}

      {/* Quick prompts above chat (optional) */}
      {quickPromptsPlacement === "above" && (
        <div className="px-2 sm:px-4 py-3 grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-full min-w-0">
          {quickPrompts.map((p) => {
            const generatePrompt = (buttonText: string) => {
              switch (buttonText) {
                case "Test":
                  return "Generate a complete test event JSON object for this tool. The JSON must include: 1) A 'state' field with a realistic game state, 2) A 'player_id' field if the tool uses it, 3) Any other parameters the tool expects. Analyze the tool's code carefully to ensure all data follows the exact format it validates (e.g., if it validates card formats like '2C', 'AH', 'KS', use that exact format). Return ONLY the complete event JSON object wrapped in ```json markers, nothing else.";
                case "Explain":
                  return "Explain what this code does step by step. Break down the logic, describe the purpose of each section, and explain how the different parts work together.";
                default:
                  return buttonText;
              }
            };
            return (
              <Button
                key={p}
                data-testid={`quick-prompt-${p.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                variant={p === "Test" ? "brand-primary" : "brand-ghost"}
                size="default"
                className="text-sm md:text-base text-left whitespace-normal break-words w-full py-3 h-auto"
                  onClick={() => {
                  // Check if there's a custom handler for Test button
                  if (p === "Test" && onTestButtonClick) {
                    const handled = onTestButtonClick();
                    if (handled) {
                      return; // Custom handler handled it, don't proceed
                    }
                  }

                  if (p === "Test") {
                    setWaitingForTestJson(true);
                  }
                  // Show LLM dialog if no model is configured
                  if (!selectedModel || !selectedModel.integrationId) {
                    onShowLLMDialog?.();
                    return;
                  }
                  onSend(generatePrompt(p), replyingTo || undefined, selectedModel);
                }}
              >
                {p}
              </Button>
            );
          })}
        </div>
      )}

      {/* Messages area with WhatsApp-style background (neutralized) */}
      <div
        ref={chatContainerRef}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain px-2 py-4 bg-transparent"
        style={{ paddingBottom: `calc(env(safe-area-inset-bottom) + ${bottomPad}px)` }}
      >

        <div className="space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 dark:text-slate-400 py-8">
              <div className="mb-3 flex items-center justify-center">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="h-6 w-6 text-brand-teal" />
                </div>
              </div>
              <p className="text-lg">{emptyTitle ?? "Hi! I'm your Tool Assistant."}</p>
              <p className="text-base mt-2">{emptySubtitle ?? "Ask me to generate code or explain tool patterns!"}</p>
            </div>
          )}
          {messages.map((m) => {
            const replyToMessage = m.replyTo ? messages.find(msg => msg.id === m.replyTo) : null;
            return (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-full md:max-w-[90%] break-words rounded-lg px-4 py-3 shadow-sm relative group ${m.role === "user"
                  ? "bg-primary text-white rounded-br-md"
                  : "bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-bl-md"
                  }`}>
                  {/* Reply indicator */}
                  {replyToMessage && (
                    <div className={`text-xs mb-2 p-2 rounded-md border-l-2 ${m.role === "user"
                      ? "bg-primary/80 border-primary/50 text-white/90"
                      : "bg-slate-100 dark:bg-slate-600 border-slate-300 dark:border-slate-500 text-slate-600 dark:text-slate-300"
                      }`}>
                      <div className="font-medium">{replyToMessage.role === "user" ? "You" : "Assistant"}</div>
                      <div className="truncate">{replyToMessage.text.substring(0, 50)}...</div>
                    </div>
                  )}

                  {/* Message sender */}
                  <div className={`text-xs font-medium mb-1 ${m.role === "user"
                    ? "text-white/80"
                    : "text-slate-500 dark:text-slate-400"
                    }`}>
                    {m.role === "user" ? "You" : "Assistant"}
                  </div>

                  {/* Message content with code parsing */}
                  <MessageContent
                    content={m.text}
                    className="text-base leading-relaxed break-words"
                    onUseCode={onUseCode}
                    onTestJsonGenerated={onTestJsonGenerated}
                    isLastAssistantMessage={m.role === "assistant" && m.id === messages.filter(msg => msg.role === "assistant").pop()?.id}
                    waitingForTestJson={waitingForTestJson}
                    onTestJsonProcessed={() => setWaitingForTestJson(false)}
                    onSendMessage={(message) => onSend(message, undefined, selectedModel || undefined)}
                    onSetWaitingForTestJson={setWaitingForTestJson}
                    onDark={m.role === "user"}
                    onTestButtonClick={onTestButtonClick}
                    isTyping={isTyping}
                  />

                  {/* Reply button (appears on hover) */}
                  <Button
                    onClick={() => setReplyingTo(m.id)}
                    variant="secondary"
                    size="sm"
                    className={`absolute top-2 opacity-0 group-hover:opacity-100 transition-opacity text-xs px-2 py-1 h-6 ${m.role === "user"
                      ? "right-2"
                      : "left-2"
                    }`}
                  >
                    Reply
                  </Button>                  {/* WhatsApp-style tail */}
                  <div className={`absolute bottom-0 w-0 h-0 ${m.role === "user"
                    ? "right-0 border-l-[8px] border-l-emerald-500 border-t-[8px] border-t-transparent"
                    : "left-0 border-r-[8px] border-r-white dark:border-r-slate-700 border-t-[8px] border-t-transparent"
                    }`} />
                </div>
              </div>
            );
          })}
          {isTyping && (
            <div className="flex justify-start">
              <div className="max-w-full md:max-w-[90%] rounded-lg rounded-bl-md px-4 py-3 bg-white dark:bg-slate-700 shadow-sm relative">
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                  <span className="text-base">Assistant is typing</span>
                  <LoadingDots />
                </div>
                {/* WhatsApp-style tail */}
                <div className="absolute bottom-0 left-0 w-0 h-0 border-r-[8px] border-r-white dark:border-r-slate-700 border-t-[8px] border-t-transparent" />
              </div>
            </div>
          )}
          <div ref={endRef} />
          {extraBelowMessages && (
            <div className="mt-3 flex justify-center">
              {extraBelowMessages}
            </div>
          )}

        </div>
      </div>
      {/* Input area */}
      <div ref={inputRef} className={`bg-muted/10 px-2 sm:px-3 py-4 ${constrainedLayout ? 'rounded-b-xl' : ''}`} style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 0px)' }}>
        {/* Reply indicator */}
        {replyingTo && (
          <div className="mb-3 p-3 bg-primary/5 dark:bg-primary/20 border border-primary/20 dark:border-primary/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="text-sm text-brand-teal dark:text-brand-teal">
                <span className="font-medium">Replying to:</span> {messages.find(m => m.id === replyingTo)?.text.substring(0, 50)}...
              </div>
              <Button
                onClick={() => setReplyingTo(null)}
                variant="ghost"
                size="sm"
                className="text-primary hover:text-accent dark:text-primary dark:hover:text-accent h-6 w-6 p-0"
              >
                ✕
              </Button>
            </div>
          </div>
        )}

        <div className="flex gap-3 items-end mb-3">
          <Textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={async (e) => {
              if (e.key === "Enter" && !e.shiftKey && draft.trim() && !isTyping) {
                e.preventDefault(); // Prevent default new line behavior
                // Show LLM dialog if no model is configured
                if (!selectedModel || !selectedModel.integrationId) {
                  onShowLLMDialog?.();
                  return;
                }
                const accepted = await Promise.resolve(onSend(draft.trim(), replyingTo || undefined, selectedModel));
                if (accepted) {
                  setDraft("");
                  setReplyingTo(null);
                }
              }
              // Shift+Enter allows new lines (default behavior)
            }}
            placeholder={isTyping ? "AI is responding..." : (!selectedModel || !selectedModel.integrationId ? "Please configure an LLM provider to use the chat feature..." : (inputPlaceholder ?? "Ask me to generate tool code... (Shift+Enter for new line)"))}
            className="flex-1 w-full rounded-lg resize-none min-h-[48px] max-h-[120px] overflow-y-auto"
            rows={1}
            disabled={isTyping}
          />
          <Button
            className="hidden sm:inline-flex w-12 h-12 flex-shrink-0"
            onClick={async () => {
              if (draft.trim() && !isTyping) {
                // Show LLM dialog if no model is configured
                if (!selectedModel || !selectedModel.integrationId) {
                  onShowLLMDialog?.();
                  return;
                }
                const accepted = await Promise.resolve(onSend(draft.trim(), replyingTo || undefined, selectedModel));
                if (accepted) {
                  setDraft("");
                  setReplyingTo(null);
                }
              }
            }}
            disabled={isTyping || !draft.trim()}
            variant="brand-primary"
            size="icon"
            aria-label="Send"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </Button>
        </div>

      </div>
    </div>
  );
};

export default VibeChat;

