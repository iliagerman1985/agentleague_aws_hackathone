import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Copy as CopyIcon } from "lucide-react";
import CodeEditor from "@/components/tools/CodeEditor";


interface MessageContentProps {
  content: string;
  className?: string;
  onUseCode?: (code: string) => void;
  onTestJsonGenerated?: (json: string) => void;
  isLastAssistantMessage?: boolean;
  waitingForTestJson?: boolean;
  onTestJsonProcessed?: () => void;
  onSendMessage?: (message: string) => void;
  onSetWaitingForTestJson?: (waiting: boolean) => void;
  onDark?: boolean; // Render text suitable for dark/colored backgrounds
  onTestButtonClick?: () => boolean; // Custom handler for Test button - return true if handled
  isTyping?: boolean; // Whether the assistant is currently typing
}

/**
 * Renders markdown content with proper styling and code block handling
 */
export const MessageContent: React.FC<MessageContentProps> = ({ content, className = "", onUseCode, onTestJsonGenerated, isLastAssistantMessage, waitingForTestJson, onTestJsonProcessed, onSendMessage, onSetWaitingForTestJson, onDark = false, onTestButtonClick, isTyping = false }) => {
  const [showOpenAPI, setShowOpenAPI] = React.useState(false);
  const [showExamples, setShowExamples] = React.useState(false);
  const [showCodeModal, setShowCodeModal] = React.useState(false);
  const [modalCode, setModalCode] = React.useState<string>("");

  // Extract test JSON from content for the useEffect hook
  // This needs to be done before any early returns to satisfy React's Rules of Hooks
  const hasJsonBlocks = /```json/i.test(content);

  // Simple extraction for the useEffect - just get the first JSON block
  const extractFirstJsonBlock = (text: string): string | null => {
    const match = /```(?:json|JSON|jsonc)\s*([\s\S]*?)```/.exec(text);
    return match ? match[1].trim() : null;
  };

  const firstJsonBlock = extractFirstJsonBlock(content);

  // If this is the last assistant message and we're waiting for test JSON, trigger the callback
  // This useEffect MUST be called before any conditional returns
  React.useEffect(() => {
    if (isLastAssistantMessage && waitingForTestJson && onTestJsonGenerated && firstJsonBlock) {
      onTestJsonGenerated(firstJsonBlock);
      onTestJsonProcessed?.();
    }
  }, [isLastAssistantMessage, waitingForTestJson, onTestJsonGenerated, firstJsonBlock, onTestJsonProcessed]);

  // Check if this is the special completion message OR if there's test JSON in the message
  // Only show for the last assistant message to avoid duplicates
  // AND only show when assistant is done typing
  const isToolComplete = content === "TOOL_GENERATION_COMPLETE";
  const shouldShowTestButton = isLastAssistantMessage && !isTyping && (isToolComplete || hasJsonBlocks);

  // If this is an old "TOOL_GENERATION_COMPLETE" message (not the last one), don't render anything
  if (isToolComplete && !isLastAssistantMessage) {
    return null;
  }

  // Handler for Test/Explain action buttons
  const handleActionClick = (action: string) => {
    // Check if there's a custom handler for Test button
    if (action === "Test" && onTestButtonClick) {
      const handled = onTestButtonClick();
      if (handled) {
        return; // Custom handler handled it, don't proceed
      }
    }

    let prompt = "";
    switch (action) {
      case "Test":
        prompt = "Generate a complete test event JSON object for this tool. The JSON must include: 1) A 'state' field with a realistic game state, 2) A 'player_id' field if the tool uses it, 3) Any other parameters the tool expects. Analyze the tool's code carefully to ensure all data follows the exact format it validates (e.g., if it validates card formats like '2C', 'AH', 'KS', use that exact format). Return ONLY the complete event JSON object wrapped in ```json markers, nothing else.";
        onSetWaitingForTestJson?.(true);
        break;
      case "Explain":
        prompt = "Explain what this code does step by step. Break down the logic, describe the purpose of each section, and explain how the different parts work together.";
        break;
    }
    if (prompt && onSendMessage) {
      onSendMessage(prompt);
    }
  };

  // Render Test button UI if needed
  if (shouldShowTestButton) {
    return (
      <div className={`${className}`}>
        {/* Mobile: compact one-liner */}
        <div className="sm:hidden">
          <div className="flex items-center gap-2 text-brand-teal dark:text-brand-teal">
            <div className="w-2 h-2 bg-brand-teal rounded-full"></div>
            <span className="font-semibold">Tool ready</span>
          </div>
          {/* Compact mobile actions */}
          <div className="mt-3 flex items-center gap-3 flex-wrap">
            <Button
              onClick={() => handleActionClick("Test")}
              className="h-9 px-4 text-sm rounded-lg min-w-[104px] bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Test
            </Button>
            <Button
              onClick={() => handleActionClick("Explain")}
              variant="outline"
              className="h-9 px-4 text-sm rounded-lg min-w-[104px]"
            >
              Explain
            </Button>
          </div>
        </div>

        {/* Desktop and up: full message with actions */}
        <div className="hidden sm:block space-y-4">
          <div className="flex items-center gap-2 text-brand-teal dark:text-brand-teal">
            <div className="w-2 h-2 bg-brand-teal rounded-full"></div>
            <span className="font-semibold">Tool Generation Complete!</span>
          </div>

          <div className="text-sm text-muted-foreground mb-4">
            Your function is ready! Choose what to do next:
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={() => handleActionClick("Test")}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-primary bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-center"
            >
              <span className="text-lg">🧪</span>
              <span className="font-medium">Test</span>
              <span className="text-xs opacity-90">Open test with sample payload</span>
            </button>

            <button
              onClick={() => handleActionClick("Explain")}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-border hover:bg-accent hover:text-accent-foreground transition-colors text-center"
            >
              <span className="text-lg">📖</span>
              <span className="font-medium">Explain</span>
              <span className="text-xs text-muted-foreground">Step-by-step breakdown</span>
            </button>
          </div>

          <div className="text-sm text-muted-foreground border-t border-border pt-3 mt-4">
            💡 <strong>Don't like the code?</strong> Continue chatting below to ask for improvements, or use the <strong>"View Code"</strong> button above to inspect your function.
          </div>
        </div>
      </div>
    );
  }

  // Custom renderer for code blocks to maintain our existing styling
  const renderCodeBlock = (code: string, language: string) => {
    const isToolFunction = language === "tool-function";
    const isTestJson = language === "json";

    return (
      <div className={`relative my-3 rounded-lg overflow-hidden no-card-hover w-full ${
        isToolFunction ? 'border-2 border-orange-200 dark:border-orange-800' :
        isTestJson ? 'border-2 border-blue-200 dark:border-blue-800' :
        'border border-slate-300 dark:border-slate-600'
      }`}>
        {/* Mobile copy action */}
        <div className="sm:hidden absolute top-2 right-2 z-10">
          <button
            onClick={() => navigator.clipboard.writeText(code)}
            className="h-8 w-8 rounded-md bg-black/30 text-white hover:bg-black/40 flex items-center justify-center"
            aria-label="Copy code"
          >
            <CopyIcon className="h-4 w-4" />
          </button>
        </div>
        {/* Code header */}
        <div className={`hidden sm:flex px-4 py-2 text-xs font-medium items-center justify-between ${
          isToolFunction
            ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300'
            : isTestJson
            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
        }`}>
          <span>
            {isToolFunction ? '🔧 Tool Function' :
             isTestJson ? '🧪 Test Payload' :
             `📝 ${language.toUpperCase()} Snippet`}
          </span>
          <div className="flex items-center gap-2">
            {onUseCode && isToolFunction && (
              <button
                onClick={() => onUseCode(code)}
                className="px-2 py-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors text-brand-teal hover:text-brand-teal/80"
                title="Use this code in the editor"
              >
                Use Code
              </button>
            )}
            {!isTestJson && (
              <button
                onClick={() => { setModalCode(code); setShowCodeModal(true); }}
                className="px-2 py-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                title="Show Code"
              >
                Show Code
              </button>
            )}
            <button
              onClick={() => navigator.clipboard.writeText(code)}
              className="px-2 py-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
              title="Copy to clipboard"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Code content */}
        <div className="bg-slate-900 text-slate-100 px-3 py-3 sm:px-5 sm:py-4 overflow-x-auto scrollbar-stable">
          <pre className="text-sm min-w-full inline-block pr-1">
            <code className={`language-${language === 'tool-function' ? 'python' : language}`}>
              {code}
            </code>
          </pre>
        </div>
      </div>
    );
  };

  // Split content into optional sections using strict headings
  const parseSections = (text: string): { desc: string | null; openapi: string | null; examples: string | null } => {
    const hDesc = "### Human-Readable Description";
    const hOpen = "### OpenAPI Schema";
    const hEx = "### Usage Examples";

    const idxDesc = text.indexOf(hDesc);
    const idxOpen = text.indexOf(hOpen);
    const idxEx = text.indexOf(hEx);

    // If none of the special headings exist, return nulls
    if (idxDesc === -1 && idxOpen === -1 && idxEx === -1) {
      return { desc: null, openapi: null, examples: null };
    }

    // Helper to take slice between this heading and the next existing heading
    const positions: Array<{ key: "desc" | "openapi" | "examples"; idx: number; label: string }> = [];
    if (idxDesc !== -1) positions.push({ key: "desc", idx: idxDesc, label: hDesc });
    if (idxOpen !== -1) positions.push({ key: "openapi", idx: idxOpen, label: hOpen });
    if (idxEx !== -1) positions.push({ key: "examples", idx: idxEx, label: hEx });

    positions.sort((a, b) => a.idx - b.idx);

    const getSlice = (startIdx: number, endIdx: number | null) => text.slice(startIdx, endIdx ?? text.length).trim();

    const result: { desc: string | null; openapi: string | null; examples: string | null } = { desc: null, openapi: null, examples: null };
    for (let i = 0; i < positions.length; i++) {
      const cur = positions[i];
      const next = positions[i + 1];
      const slice = getSlice(cur.idx, next ? next.idx : null);
      if (cur.key === "desc") result.desc = slice;
      if (cur.key === "openapi") result.openapi = slice;
      if (cur.key === "examples") result.examples = slice;
    }
    return result;
  };

  const sections = parseSections(content);

  const markdownComponents = {
    // Custom code block renderer
    code: ({ className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      if (language) {
        return renderCodeBlock(String(children).replace(/\n$/, ''), language);
      }
      return (
        <code
          className={`${onDark ? 'bg-white/10 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'} px-1.5 py-0.5 rounded text-sm font-mono`}
          {...props}
        >
          {children}
        </code>
      );
    },
    // Style headers
    h1: ({ children }: any) => (
      <h1 className={`text-2xl font-bold mb-4 mt-6 first:mt-0 ${onDark ? 'text-white' : 'text-slate-900 dark:text-slate-100'}`}>{children}</h1>
    ),
    h2: ({ children }: any) => (
      <h2 className={`text-xl font-bold mb-3 mt-5 first:mt-0 ${onDark ? 'text-white' : 'text-slate-900 dark:text-slate-100'}`}>{children}</h2>
    ),
    h3: ({ children }: any) => (
      <h3 className={`text-lg font-semibold mb-2 mt-4 first:mt-0 ${onDark ? 'text-white' : 'text-slate-900 dark:text-slate-100'}`}>{children}</h3>
    ),
    // Style lists
    ul: ({ children }: any) => (
      <ul className={`list-disc list-inside mb-4 last:mb-0 space-y-1 ${onDark ? 'text-white/90' : 'text-slate-700 dark:text-slate-300'}`}>{children}</ul>
    ),
    ol: ({ children }: any) => (
      <ol className={`list-decimal list-inside mb-4 last:mb-0 space-y-1 ${onDark ? 'text-white/90' : 'text-slate-700 dark:text-slate-300'}`}>{children}</ol>
    ),
    li: ({ children }: any) => <li className="ml-4">{children}</li>,
    // Style paragraphs
    p: ({ children }: any) => (
      <p className={`mb-3 last:mb-0 leading-relaxed ${onDark ? 'text-white' : 'text-slate-700 dark:text-slate-300'}`}>{children}</p>
    ),
    // Style strong/bold text
    strong: ({ children }: any) => (
      <strong className={`font-semibold ${onDark ? 'text-white' : 'text-slate-900 dark:text-slate-100'}`}>{children}</strong>
    ),
    // Style emphasis/italic text
    em: ({ children }: any) => <em className={`italic ${onDark ? 'text-white/90' : 'text-slate-700 dark:text-slate-300'}`}>{children}</em>,
    blockquote: ({ children }: any) => (
      <blockquote className={`${onDark ? 'border-white/40 text-white/80' : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400'} border-l-4 pl-4 my-4 first:mt-0 last:mb-0 italic`}>{children}</blockquote>
    ),
  } as const;

  // Helper to render markdown with shared components
  const renderMarkdown = (md: string) => (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {md}
    </ReactMarkdown>
  );

  // Remove a leading ### Heading line (we show our own modal titles)
  const stripLeadingH3 = (md: string): string => md.replace(/^###\s+[^\n]+\n?/, "").trim();

  // Extract only JSON code blocks from a markdown string (ignore any commentary)
  const extractJsonBlocks = (md: string): string[] => {
    // 1) Prefer fenced ```json blocks
    const fencedRegex = /```(?:json|JSON|jsonc)\s*([\s\S]*?)```/g;
    const blocks: string[] = [];
    let match: RegExpExecArray | null;
    while ((match = fencedRegex.exec(md)) !== null) {
      let block = match[1] ?? "";
      block = block
        .split("\n")
        .filter((line) => !/^\s*(\/\/|#)/.test(line))
        .join("\n")
        .trim();
      if (block) blocks.push(block);
    }
    if (blocks.length > 0) return blocks;

    // 2) If none found, strip other code fences and try to capture inline JSON objects
    const stripNonJsonFences = (text: string) => text.replace(/```(?!json|JSON|jsonc)[\s\S]*?```/g, "");

    const cleaned = stripNonJsonFences(md);

    // Balance-brace scan to capture JSON-looking objects
    const inlineBlocks: string[] = [];
    let depth = 0;
    let start = -1;
    for (let i = 0; i < cleaned.length; i++) {
      const ch = cleaned[i];
      if (ch === "{") {
        if (depth === 0) start = i;
        depth++;
      } else if (ch === "}") {
        if (depth > 0) depth--;
        if (depth === 0 && start !== -1) {
          let candidate = cleaned.slice(start, i + 1).trim();
          // Remove obvious comment lines inside
          candidate = candidate
            .split("\n")
            .filter((line) => !/^\s*(\/\/|#)/.test(line))
            .join("\n")
            .trim();
          // Heuristic: must contain a colon or quoted key to look like JSON
          if (/:|"/.test(candidate)) inlineBlocks.push(candidate);
          start = -1;
        }
      }
    }

    return inlineBlocks;
  };

  // Prefer JSON from the Examples section; if absent, fall back to scanning the whole message
  const exampleJsonBlocks = sections.examples
    ? extractJsonBlocks(stripLeadingH3(sections.examples))
    : extractJsonBlocks(content);

  const hasSpecialSections = Boolean(sections.desc || sections.openapi || sections.examples);

  return (
    <div className={`markdown-reset ${className || ""}`}>
      {hasSpecialSections ? (
        <div>
          {/* Human-Readable Description (visible) */}
          {sections.desc && renderMarkdown(sections.desc)}

          {/* OpenAPI (collapsed by default) */}
          {sections.openapi && (
            <div className="mt-3">
              <Button variant="outline" size="sm" onClick={() => setShowOpenAPI(true)}>
                View OpenAPI
              </Button>
            </div>
          )}

          {/* Usage Examples (open in modal) */}
          {sections.examples && (
            <div className="mt-2">
              <Button variant="outline" size="sm" onClick={() => setShowExamples(true)}>
                View Examples
              </Button>
            </div>
          )}
        </div>
      ) : (
        renderMarkdown(content)
      )}

      {/* Modals for OpenAPI, Examples, and Code */}
      <Dialog open={showOpenAPI} onOpenChange={setShowOpenAPI}>
        <DialogContent className="max-w-[min(1200px,90vw)] w-[90vw]">
          <DialogHeader>
            <DialogTitle>OpenAPI Schema</DialogTitle>
          </DialogHeader>
          <div className="mt-2 max-h-[80vh] overflow-y-auto pr-2 scrollbar-stable">
            {sections.openapi && renderMarkdown(stripLeadingH3(sections.openapi))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showExamples} onOpenChange={setShowExamples}>
        <DialogContent className="max-w-[min(1200px,90vw)] w-[90vw]">
          <DialogHeader>
            <DialogTitle>Usage Examples</DialogTitle>
          </DialogHeader>
          <div className="mt-2 max-h-[80vh] overflow-y-auto pr-2 scrollbar-stable">
            {exampleJsonBlocks.length > 0
              ? exampleJsonBlocks.map((j, i) => (
                  <div key={i}>{renderCodeBlock(j, "json")}</div>
                ))
              : sections.examples && renderMarkdown(stripLeadingH3(sections.examples))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showCodeModal} onOpenChange={setShowCodeModal}>
        <DialogContent className="max-w-[min(1200px,90vw)] w-[90vw]">
          <DialogHeader>
            <DialogTitle>Code</DialogTitle>
          </DialogHeader>
          <div className="mt-2 max-h-[80vh] overflow-y-auto pr-2 scrollbar-stable">
            <CodeEditor value={modalCode} language="python" onChange={() => {}} readOnly height="60vh" />
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                try { navigator.clipboard.writeText(modalCode || ""); } catch {}
                setShowCodeModal(false);
              }}
            >
              Copy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MessageContent;