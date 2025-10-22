import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Book, Code, LifeBuoy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { GettingStartedContent } from "./topics/GettingStartedContent";
import { AgentConfigurationContent } from "./topics/AgentConfigurationContent";
import { ToolsAndFunctionsContent } from "./topics/ToolsAndFunctionsContent";
import { SystemPromptGuideContent } from "./topics/SystemPromptGuideContent";
import { GameEnvironmentsContent } from "./topics/GameEnvironmentsContent";
import { APIReferenceContent } from "./topics/APIReferenceContent";

interface HelpTopic {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

const helpTopics: HelpTopic[] = [
  {
    id: "getting-started",
    title: "Getting Started",
    description: "An overview of the platform and how to create your first agent.",
    icon: <Book className="h-6 w-6" />,
    content: <GettingStartedContent />,
  },
  {
    id: "agent-configuration",
    title: "Agent Configuration",
    description: "Learn how to configure your agent's settings, including LLMs and execution parameters.",
    icon: <Book className="h-6 w-6" />,
    content: <AgentConfigurationContent />,
  },
  {
    id: "tools-functions",
    title: "Tools & Functions",
    description: "Understand how to create and use custom tools for your agents.",
    icon: <Code className="h-6 w-6" />,
    content: <ToolsAndFunctionsContent />,
  },
  {
    id: "system-prompt-guide",
    title: "System Prompt Guide",
    description: "A guide to writing effective system prompts for your agents.",
    icon: <Book className="h-6 w-6" />,
    content: <SystemPromptGuideContent />,
  },
  {
    id: "game-environments",
    title: "Game Environments",
    description: "Details about the supported game environments and their state variables.",
    icon: <LifeBuoy className="h-6 w-6" />,
    content: <GameEnvironmentsContent />,
  },
  {
    id: "api-reference",
    title: "API Reference",
    description: "Full API documentation for programmatic access.",
    icon: <Code className="h-6 w-6" />,
    content: <APIReferenceContent />,
  },
];

export const HelpDetailPage: React.FC = () => {
  const { topicId } = useParams<{ topicId: string }>();
  const navigate = useNavigate();

  const topic = helpTopics.find((t) => t.id === topicId);

  if (!topic) {
    return (
      <div className="w-full space-y-8 p-6 lg:p-8">
        <div className="w-full max-w-[95rem] mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>Topic Not Found</CardTitle>
              <CardDescription>The help topic you're looking for doesn't exist.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => navigate("/help")}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Help
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-8 p-6 lg:p-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        {/* Header */}
        <div className="relative flex items-center justify-between mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="help" opacity={0.20} />
          </div>
          <div className="relative z-10 flex-1">
            <div className="flex items-center gap-4 mb-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/help")}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Help
              </Button>
            </div>
            <div className="flex items-center gap-4">
              <div className="bg-primary/10 text-primary flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full">
                {topic.icon}
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2">
                  {topic.title}
                </h1>
                <p className="hidden sm:block text-muted-foreground text-lg">
                  {topic.description}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="prose prose-slate dark:prose-invert max-w-none">
          {topic.content}
        </div>
      </div>
    </div>
  );
};

export default HelpDetailPage;

