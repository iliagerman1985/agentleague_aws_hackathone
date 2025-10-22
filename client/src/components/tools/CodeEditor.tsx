import React, { useEffect } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { EditorView } from "@codemirror/view";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags as t } from "@lezer/highlight";
import { ScrollableEditorShell } from "@/components/common/editor/ScrollableEditorShell";

export interface CodeEditorProps {
  value: string;
  language?: "python" | "text";
  onChange: (code: string) => void;
  onSave?: () => void;
  onRun?: () => void;
  className?: string;
  height?: string; // e.g., "100%" to fill parent
  maxHeight?: string; // pass-through to ScrollableEditorShell (e.g., "none" for page scroll)
  readOnly?: boolean; // render as read-only viewer
}

// Custom theme that uses CSS variables from our theme
const customTheme = EditorView.theme(
  {
    "&": {
      color: "hsl(var(--foreground))",
      backgroundColor: "hsl(var(--card))",
    },
    ".cm-content": {
      caretColor: "hsl(var(--foreground))",
      backgroundColor: "hsl(var(--card))",
    },
    "&.cm-focused .cm-cursor": {
      borderLeftColor: "hsl(var(--foreground))",
    },
    "&.cm-focused .cm-selectionBackground, ::selection": {
      backgroundColor: "hsl(var(--accent) / 0.2)",
    },
    ".cm-gutters": {
      backgroundColor: "hsl(var(--card))",
      color: "hsl(var(--muted-foreground) / 0.5)",
      border: "none",
    },
    ".cm-activeLineGutter": {
      backgroundColor: "hsl(var(--muted) / 0.2)",
    },
    ".cm-activeLine": {
      backgroundColor: "hsl(var(--muted) / 0.1)",
    },
    ".cm-line": {
      paddingLeft: "12px",
    }
  },
  { dark: false } // Let the theme adapt to the current color scheme
);

// Custom syntax highlighting for Python using vibrant colors
const customHighlightStyle = HighlightStyle.define([
  { tag: t.keyword, color: "#8B5CF6", fontWeight: "bold" }, // violet for keywords
  { tag: [t.string, t.special(t.string)], color: "#F59E0B" }, // amber for strings
  { tag: t.number, color: "#10B981" }, // emerald for numbers
  { tag: [t.bool, t.null], color: "#EF4444", fontWeight: "bold" }, // red for booleans/null
  { tag: t.variableName, color: "#06B6D4" }, // cyan for variables
  { tag: t.function(t.variableName), color: "#3B82F6", fontWeight: "600" }, // blue for functions
  { tag: t.className, color: "#F97316", fontWeight: "600" }, // orange for classes
  { tag: [t.comment], color: "#9CA3AF", fontStyle: "italic" }, // gray for comments
  { tag: [t.punctuation, t.bracket], color: "#9CA3AF" }, // gray for punctuation
  { tag: t.brace, color: "#D1D5DB" }, // light gray for braces
  { tag: t.operator, color: "#EC4899" }, // pink for operators
  { tag: t.definition(t.variableName), color: "#06B6D4", fontWeight: "600" }, // cyan for definitions
]);

const brandEditorTweaks = EditorView.theme({
  ".cm-editor": {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace",
    fontSize: "14px",
    lineHeight: "1.6",
    height: "100%",
    width: "100%",
  },
  ".cm-scroller": {
    fontFamily: "inherit",
    scrollbarWidth: "thin",
    scrollbarColor: "hsl(var(--muted-foreground) / 0.3) hsl(var(--muted))",
    height: "100%",
    width: "100%",
    backgroundColor: "hsl(var(--card))",

    scrollbarGutter: "stable",
    paddingRight: "0px",
    overscrollBehavior: "contain",
    overflow: "visible", // let the shell handle scrolling to avoid nested scrollbars
    "&::-webkit-scrollbar": {
      width: "8px",
      height: "8px",
    },
    "&::-webkit-scrollbar-track": {
      background: "hsl(var(--card))",
      borderRadius: "4px",
    },
    "&::-webkit-scrollbar-thumb": {
      background: "hsl(var(--muted-foreground) / 0.3)",
      borderRadius: "4px",
      transition: "background-color 0.2s ease",
    },
    "&::-webkit-scrollbar-thumb:hover": {
      background: "hsl(var(--muted-foreground) / 0.5)",
    },
  },
  ".cm-gutters": {
    borderRight: "1px solid hsl(var(--border))",
  },
  ".cm-content": {
    padding: "20px 16px 16px 16px",
  },
  ".cm-focused": {
    outline: "none",
  },
});

export const CodeEditor: React.FC<CodeEditorProps> = ({ value, language = "python", onChange, onSave, onRun, className, height, maxHeight, readOnly = false }) => {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      const isCmd = e.metaKey || e.ctrlKey;
      if (isCmd && e.key.toLowerCase() === "s") {
        e.preventDefault();
        onSave?.();
      } else if (isCmd && e.key === "Enter") {
        e.preventDefault();
        onRun?.();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onSave, onRun]);

  const extensions = [
    customTheme,
    brandEditorTweaks,
    syntaxHighlighting(customHighlightStyle),
    ...(language === "python" ? [python()] : []),
    ...(readOnly ? [EditorView.editable.of(false)] : [])
  ];

  return (
    <ScrollableEditorShell
      className={`no-card-hover ${className ?? ""}`}
      maxHeight={maxHeight ?? "65vh"}
      data-testid="code-editor"
    >
      <CodeMirror
        value={value}
        height={height ?? "100%"}
        basicSetup={{
          bracketMatching: true,
          highlightActiveLine: true,
          indentOnInput: true,
          lineNumbers: true,
        }}
        extensions={extensions}
        onChange={(v) => onChange(v)}
      />
      <div className="pointer-events-none absolute right-3 top-3 text-sm text-foreground bg-brand-teal/90 px-3 py-1 rounded-lg shadow-sm">
        {language?.toUpperCase?.() ?? ""}
      </div>
    </ScrollableEditorShell>
  );
};

export default CodeEditor;

