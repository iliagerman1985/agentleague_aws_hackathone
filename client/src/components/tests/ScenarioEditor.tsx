import React, { useEffect, useMemo, useState } from "react";
import { json } from "@codemirror/lang-json";
import CodeMirror from "@uiw/react-codemirror";
import { AgentId } from "@/types/ids";
import { LLMSelectorWrapper } from "@/components/common/llm/LLMSelectorWrapper";
import { ScrollableEditorShell } from "@/components/common/editor/ScrollableEditorShell";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PanelLeft, MessageSquareText } from "lucide-react";
import StateChatDialog from "@/components/pages/agents/dialogs/StateChatDialog";

interface ScenarioEditorProps {
  value: Record<string, any>;
  description?: string;
  onChange: (state: Record<string, any>, description?: string) => void;
  agentIdForChat?: AgentId | null;
  showExecutionLogButton?: boolean;
  onOpenExecutionLog?: () => void;
}

export const ScenarioEditor: React.FC<ScenarioEditorProps> = ({ value, description, onChange, agentIdForChat, showExecutionLogButton = false, onOpenExecutionLog }) => {
  const [activeTab, setActiveTab] = useState<"json" | "chat">("json");
  const [chatOpen, setChatOpen] = useState<boolean>(false);
  const [jsonText, setJsonText] = useState<string>(() => JSON.stringify(value ?? {}, null, 2));
  const [desc, setDesc] = useState<string>(description ?? "");

  useEffect(() => {
    // keep external value in sync when it changes (e.g., load from server)
    setJsonText(JSON.stringify(value ?? {}, null, 2));
    setDesc(description ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(value), description]);

  const parsedState = useMemo(() => {
    try {
      return JSON.parse(jsonText);
    } catch {
      return null;
    }
  }, [jsonText]);

  useEffect(() => {
    if (parsedState) onChange(parsedState, desc);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jsonText, desc]);

  return (
    <div className="w-full space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <PanelLeft className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Scenario Editor</span>
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <div className="hidden md:flex"><LLMSelectorWrapper context="global" compact label="LLM" /></div>
          <Button
            variant={chatOpen ? "brand-primary" : "outline"}
            size="sm"
            onClick={() => { setActiveTab("chat"); setChatOpen(true); }}
            disabled={!agentIdForChat}
          >
            <MessageSquareText className="h-4 w-4 mr-1" /> Chat Edit
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <div className="flex items-center gap-2 flex-wrap w-full">
          <TabsList className="order-1">
            <TabsTrigger value="json">JSON</TabsTrigger>
            <TabsTrigger value="chat" disabled={!agentIdForChat} onClick={() => setChatOpen(true)}>Chat</TabsTrigger>
          </TabsList>
          {showExecutionLogButton && (
            <Button
              variant="outline"
              size="sm"
              className="order-2 md:ml-auto"
              onClick={() => onOpenExecutionLog?.()}
            >
              Execution Log
            </Button>
          )}
        </div>

        <TabsContent value="json" className="mt-3">
          <ScrollableEditorShell maxHeight="60vh" backgroundClassName="bg-card" borderClassName="border-border">
            <CodeMirror
              value={jsonText}
              height="60vh"
              extensions={[json()]}
              theme={"dark"}
              onChange={setJsonText}
            />
          </ScrollableEditorShell>
        </TabsContent>

        <TabsContent value="chat" className="mt-3">
          {!agentIdForChat ? (
            <div className="text-sm text-muted-foreground">Select an agent above to enable chat editing.</div>
          ) : (
            <>
              <div className="text-sm text-muted-foreground mb-2">Use the button above to open the chat editor.</div>
              <StateChatDialog
                open={chatOpen}
                onOpenChange={setChatOpen}
                agentId={agentIdForChat}
                initialState={parsedState ?? {}}
                initialDescription={desc}
                onApply={(finalState, finalDesc) => {
                  setJsonText(JSON.stringify(finalState ?? {}, null, 2));
                  setDesc(finalDesc ?? "");
                  onChange(finalState ?? {}, finalDesc);
                  setChatOpen(false);
                }}
              />
            </>
          )}
        </TabsContent>
      </Tabs>

      <div className="space-y-2">
        <label className="text-sm text-muted-foreground">Description</label>
        <textarea
          className="w-full min-h-24 rounded-md border bg-background p-2 text-sm mb-16"
          placeholder="Describe this scenario..."
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
        />
      </div>
    </div>
  );
};

