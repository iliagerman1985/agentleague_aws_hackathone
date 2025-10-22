import React from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { ItemCard } from "@/components/common/cards/ItemCard";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { Book, Code, LifeBuoy, Search } from "lucide-react";

interface HelpDoc {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const helpDocs: HelpDoc[] = [
  {
    id: "getting-started",
    title: "Getting Started",
    description: "An overview of the platform and how to create your first agent.",
    icon: <Book />
  },
  {
    id: "agent-configuration",
    title: "Agent Configuration",
    description: "Learn how to configure your agent's settings, including LLMs and execution parameters.",
    icon: <Book />
  },
  {
    id: "tools-functions",
    title: "Tools & Functions",
    description: "Understand how to create and use custom tools for your agents.",
    icon: <Code />
  },
  {
    id: "system-prompt-guide",
    title: "System Prompt Guide",
    description: "A guide to writing effective system prompts for your agents.",
    icon: <Book />
  },
  {
    id: "game-environments",
    title: "Game Environments",
    description: "Details about the supported game environments and their state variables.",
    icon: <LifeBuoy />
  },
  {
    id: "api-reference",
    title: "API Reference",
    description: "Full API documentation for programmatic access.",
    icon: <Code />
  },
];

export const Help: React.FC = () => {
  const [searchQuery, setSearchQuery] = React.useState("");
  const navigate = useNavigate();

  const filteredDocs = helpDocs.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDocClick = (docId: string) => {
    navigate(`/help/${docId}`);
  };

  return (
    <div className="w-full space-y-8 p-6 lg:p-8">
      <div className="w-full max-w-[95rem] mx-auto space-y-8">
        <div className="relative flex items-center justify-between mb-8 bg-card/30 backdrop-blur-sm rounded-xl border border-border/50 p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-xl">
            <EnvironmentBackground environment="help" opacity={0.20} />
          </div>
          <div className="relative z-10">
            <h1 className="text-2xl sm:text-4xl font-bold text-foreground mb-0 sm:mb-2 truncate max-w-[70vw] sm:max-w-none sm:whitespace-normal">Help</h1>
            <p className="hidden sm:block text-muted-foreground text-lg">Product documentation and support</p>
          </div>
        </div>
        <div className="space-y-6">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4 z-10 pointer-events-none" />
            <Input
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredDocs.map((doc) => (
              <ItemCard
                key={doc.id}
                icon={doc.icon}
                title={doc.title}
                description={doc.description}
                onClick={() => handleDocClick(doc.id)}
                clickable
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Help;
