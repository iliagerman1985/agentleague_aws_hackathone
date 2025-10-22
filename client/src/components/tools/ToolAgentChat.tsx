/**
 * Tool Agent Chat Component
 * Specialized chat interface for tool creation using Strands agent
 */

import React, { useState, useRef, useEffect } from "react";
import { Send, Code, FlaskConical, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AgentMessage, ToolArtifact, TestArtifact } from "@/services/toolAgentService";

interface ToolAgentChatProps {
  messages: AgentMessage[];
  onSend: (message: string) => void;
  isTyping: boolean;
  onApplyCode?: (code: string) => void;
  onApplyTest?: (testState: Record<string, any>) => void;
  environment?: string;
}

export const ToolAgentChat: React.FC<ToolAgentChatProps> = ({
  messages,
  onSend,
  isTyping,
  onApplyCode,
  onApplyTest,
  environment,
}) => {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = () => {
    if (input.trim() && !isTyping) {
      onSend(input.trim());
      setInput("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderToolArtifact = (artifact: ToolArtifact) => (
    <Card className="mt-2 p-3 bg-brand-teal/10 border-brand-teal/30">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Code className="h-4 w-4 text-brand-teal" />
            <span className="font-semibold text-sm">
              {artifact.displayName ?? artifact.display_name ?? "Tool Code"}
            </span>
          </div>
          {artifact.description && (
            <p className="text-sm text-muted-foreground mb-2">
              {artifact.description}
            </p>
          )}
          {(artifact.validationStatus ?? artifact.validation_status) && (
            <span
              className={`text-xs px-2 py-1 rounded ${
                (artifact.validationStatus ?? artifact.validation_status) === "valid"
                  ? "bg-green-100 text-green-800"
                  : "bg-yellow-100 text-yellow-800"
              }`}
            >
              {artifact.validationStatus ?? artifact.validation_status}
            </span>
          )}
        </div>
        {artifact.code && onApplyCode && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onApplyCode(artifact.code!)}
            className="ml-2"
          >
            Apply Code
          </Button>
        )}
      </div>
    </Card>
  );

  const renderTestArtifact = (artifact: TestArtifact) => (
    <Card className="mt-2 p-3 bg-brand-orange/10 border-brand-orange/30">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <FlaskConical className="h-4 w-4 text-brand-orange" />
            <span className="font-semibold text-sm">
              {artifact.name || "Test Scenario"}
            </span>
          </div>
          {artifact.description && (
            <p className="text-sm text-muted-foreground mb-2">
              {artifact.description}
            </p>
          )}
          {artifact.environment && (
            <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-800">
              {artifact.environment}
            </span>
          )}
        </div>
        {artifact.game_state && onApplyTest && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onApplyTest(artifact.game_state!)}
            className="ml-2"
          >
            Apply Test
          </Button>
        )}
      </div>
    </Card>
  );

  const renderMessage = (message: AgentMessage, index: number) => {
    const isHuman = message.writer === "human";

    return (
      <div
        key={index}
        className={`flex ${isHuman ? "justify-end" : "justify-start"} mb-4`}
      >
        <div className={`max-w-[80%] ${isHuman ? "order-2" : "order-1"}`}>
          <div
            className={`rounded-lg p-3 ${
              isHuman
                ? "bg-brand-teal text-white"
                : "bg-card border border-border"
            }`}
          >
            {message.content && (
              <div className="whitespace-pre-wrap text-sm">
                {message.content}
              </div>
            )}
            {message.tool_artifact && renderToolArtifact(message.tool_artifact)}
            {message.test_artifact && renderTestArtifact(message.test_artifact)}
          </div>
          <div
            className={`text-xs text-muted-foreground mt-1 ${
              isHuman ? "text-right" : "text-left"
            }`}
          >
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Environment indicator */}
      {environment && (
        <div className="px-4 py-2 bg-muted/50 border-b">
          <span className="text-sm text-muted-foreground">
            Environment: <span className="font-semibold">{environment}</span>
          </span>
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-lg font-semibold mb-2">
              Tool Creation Assistant
            </p>
            <p className="text-sm">
              Ask me to create, modify, or test tools for your agents.
            </p>
            <div className="mt-4 text-left max-w-md mx-auto space-y-2">
              <p className="text-xs font-semibold">Try asking:</p>
              <ul className="text-xs space-y-1 list-disc list-inside">
                <li>"Create a pot odds calculator for poker"</li>
                <li>"Generate a test scenario for this tool"</li>
                <li>"Fix the validation errors in my code"</li>
                <li>"Show me examples of chess evaluation tools"</li>
              </ul>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => renderMessage(msg, idx))}

        {isTyping && (
          <div className="flex justify-start mb-4">
            <div className="bg-card border border-border rounded-lg p-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-brand-teal" />
                <span className="text-sm text-muted-foreground">
                  Agent is thinking...
                </span>
              </div>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me to create, modify, or test a tool..."
            className="min-h-[60px] max-h-[200px] resize-none"
            disabled={isTyping}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            size="icon"
            className="h-[60px] w-[60px]"
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};

export default ToolAgentChat;

