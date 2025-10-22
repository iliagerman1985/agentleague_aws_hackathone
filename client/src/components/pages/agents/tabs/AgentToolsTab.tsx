import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toolsService, type Tool, type GameEnvironment as ToolGameEnvironment } from "@/services/toolsService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EnvironmentBackground } from "@/components/art/EnvironmentBackground";
import { GameEnvironment } from "@/services/agentsService";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Wrench, Plus, ArrowUp, ArrowDown, MinusCircle } from "lucide-react";
import { type ToolId } from "@/types/ids";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface AgentToolsTabProps {
  toolIds: ToolId[];
  onToolIdsChange: (toolIds: ToolId[]) => void;
  environment?: GameEnvironment;
}

export const AgentToolsTab: React.FC<AgentToolsTabProps> = ({
  toolIds,
  onToolIdsChange,
  environment,
}) => {
  const [availableTools, setAvailableTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  // Extract only the human-readable description from the tool description
  const extractHumanReadableDescription = (text: string): string => {
    if (!text) return "";
    
    const hDesc = "### Human-Readable Description";
    const hOpen = "### OpenAPI Schema";
    const hEx = "### Usage Examples";

    const idxDesc = text.indexOf(hDesc);
    const idxOpen = text.indexOf(hOpen);
    const idxEx = text.indexOf(hEx);

    // If no structured sections found, return the original text (truncated)
    if (idxDesc === -1 && idxOpen === -1 && idxEx === -1) {
      return text.length > 200 ? text.substring(0, 200) + "..." : text;
    }

    // If human-readable section exists, extract just that part
    if (idxDesc !== -1) {
      const positions = [];
      if (idxOpen !== -1) positions.push(idxOpen);
      if (idxEx !== -1) positions.push(idxEx);
      
      const nextIdx = positions.length > 0 ? Math.min(...positions) : undefined;
      const slice = text.slice(idxDesc + hDesc.length, nextIdx).trim();
      return slice || text.substring(0, 200) + "...";
    }

    // If no human-readable section but other sections exist, return first 200 chars
    return text.length > 200 ? text.substring(0, 200) + "..." : text;
  };

  // Truncate text to a maximum number of words (used for mobile descriptions)
  const truncateWords = (text: string, maxWords: number): string => {
    const words = text.trim().split(/\s+/);
    return words.length > maxWords ? words.slice(0, maxWords).join(" ") + "..." : text.trim();
  };

  useEffect(() => {
    loadTools();
  }, [environment]);

  const loadTools = async () => {
    try {
      // Filter tools by environment if environment is provided
      const tools = environment
        ? await toolsService.list(environment as ToolGameEnvironment)
        : await toolsService.list();
      setAvailableTools(tools);
    } catch (error) {
      console.error("Failed to load tools:", error);
    } finally {
      setLoading(false);
    }
  };

  // const selectedTools = availableTools.filter(tool => toolIds.includes(tool.id));
  const unselectedTools = availableTools.filter(tool => !toolIds.includes(tool.id));

  const filteredUnselectedTools = unselectedTools.filter(tool => {
    const humanReadableDesc = tool.description ? extractHumanReadableDescription(tool.description) : "";
    const query = searchQuery.toLowerCase();
    // Prefer display_name for searching; fall back to internal name
    return (
      ((tool.displayName || tool.name) as string).toLowerCase().includes(query) ||
      humanReadableDesc.toLowerCase().includes(query)
    );
  });

  const handleToolToggle = (toolId: ToolId, isSelected: boolean) => {
    if (isSelected) {
      // Add tool
      if (toolIds.length < 10) {
        onToolIdsChange([...toolIds, toolId]);
      }
    } else {
      // Remove tool
      onToolIdsChange(toolIds.filter(id => id !== toolId));
    }
  };

  const moveToolUp = (index: number) => {
    if (index === 0) return;
    const newToolIds = [...toolIds];
    [newToolIds[index - 1], newToolIds[index]] = [newToolIds[index], newToolIds[index - 1]];
    onToolIdsChange(newToolIds);
  };

  const moveToolDown = (index: number) => {
    if (index === toolIds.length - 1) return;
    const newToolIds = [...toolIds];
    [newToolIds[index], newToolIds[index + 1]] = [newToolIds[index + 1], newToolIds[index]];
    onToolIdsChange(newToolIds);
  };

  const getToolById = (id: ToolId) => availableTools.find(tool => tool.id === id);

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-teal mx-auto mb-4"></div>
        <p className="text-muted-foreground">Loading tools...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-2">Tool Selection</h3>
        <p className="text-muted-foreground">
          Select 1-10 tools for your agent to use. Tools will be executed in the order shown below.
        </p>
      </div>

      {/* Selected Tools */}
      <Card className="relative overflow-hidden">
        <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Selected Tools ({toolIds.length}/10)
          </CardTitle>
          <CardDescription>
            Use the arrow buttons to reorder tools. Tools will be available to your agent in this order.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {toolIds.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No tools selected</p>
              <p className="text-sm">Add tools to enhance your agent's capabilities (optional).</p>
            </div>
          ) : (
            <div className="space-y-2">
              {toolIds.map((toolId, index) => {
                const tool = getToolById(toolId);
                if (!tool) return null;

                return (
                  <div
                    key={toolId}
                    className="flex w-full items-center gap-3 p-3 pr-5 bg-muted/30 rounded-lg border"
                  >
                    <Badge variant="outline" className="text-xs">
                      {index + 1}
                    </Badge>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="font-medium text-foreground">{tool.displayName || tool.name}</div>
                        <Badge variant="outline" className="text-xs">
                          {tool.environment === 'texas_holdem' ? 'Texas Hold\'em' : 'Chess'}
                        </Badge>
                        {tool.validationStatus !== 'valid' && (
                          <Badge variant="destructive" className="text-xs">{tool.validationStatus.toUpperCase()}</Badge>
                        )}
                      </div>
                      {tool.description && (
                        <div className="text-sm text-muted-foreground line-clamp-1">
                          {extractHumanReadableDescription(tool.description)}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => moveToolUp(index)}
                        disabled={index === 0}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => moveToolDown(index)}
                        disabled={index === toolIds.length - 1}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              aria-label="Remove tool"
                              variant="ghost"
                              size="icon"
                              onClick={() => handleToolToggle(toolId, false)}
                              className="rounded-full text-muted-foreground hover:text-foreground"
                            >
                              <MinusCircle className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Remove</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Tools */}
      <Card className="relative overflow-hidden">
        <EnvironmentBackground environment={environment} opacity={0.05} className="absolute inset-0 pointer-events-none" />
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Available Tools
            </CardTitle>
            <Button
              variant="brand-primary"
              size="sm"
              onClick={() => {
                const returnTo = encodeURIComponent(location.pathname + location.search);
                navigate(`/tools/new?returnTo=${returnTo}`);
              }}
              data-testid="create-tool-from-agent"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Tool
            </Button>
          </div>
          <CardDescription>
            Select tools to add to your agent. You can select up to 10 tools total.
            {environment && (
              <span className="block mt-1 text-xs text-muted-foreground">
                Showing tools compatible with <span className="font-semibold">{environment === 'texas_holdem' ? 'Texas Hold\'em' : 'Chess'}</span> environment.
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              placeholder="Search available tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Tools List */}
          <div className="grid gap-2 max-h-[400px] overflow-y-auto scrollbar-stable pt-2">
            {filteredUnselectedTools.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {availableTools.length === 0 ? (
                  <>
                    <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="mb-2">No tools available yet</p>
                    <p className="text-sm mb-4">Create your first tool to enable tool selection for this agent.</p>
                    <Button
                      variant="brand-primary"
                      onClick={() => {
                        const returnTo = encodeURIComponent(location.pathname + location.search);
                        navigate(`/tools/new?returnTo=${returnTo}`);
                      }}
                      data-testid="create-first-tool-button"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Create The First Tool
                    </Button>
                  </>
                ) : searchQuery ? (
                  <>
                    <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No tools found matching "{searchQuery}"</p>
                  </>
                ) : (
                  <>
                    <Wrench className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>All available tools are already selected</p>
                  </>
                )}
              </div>
            ) : (
              filteredUnselectedTools.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-start gap-3 p-3 bg-background rounded-lg border hover:bg-muted/30 transition-colors"
                >
                  <Checkbox
                    checked={false}
                    onCheckedChange={() => handleToolToggle(tool.id, true)}
                    disabled={toolIds.length >= 10}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="font-medium text-foreground">{tool.displayName || tool.name}</div>
                      <Badge variant="outline" className="text-xs">
                        {tool.environment === 'texas_holdem' ? 'Texas Hold\'em' : 'Chess'}
                      </Badge>
                      {tool.validationStatus !== 'valid' && (
                        <Badge variant="secondary" className="text-xs">{tool.validationStatus.toUpperCase()}</Badge>
                      )}
                    </div>
                    {tool.description && (
                      <>
                        {/* Mobile: limit to 20 words with ellipsis */}
                        <div className="text-sm text-muted-foreground sm:hidden">
                          {truncateWords(extractHumanReadableDescription(tool.description), 20)}
                        </div>
                        {/* Desktop and up: full description */}
                        <div className="text-sm text-muted-foreground hidden sm:block">
                          {extractHumanReadableDescription(tool.description)}
                        </div>
                      </>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToolToggle(tool.id, true)}
                    disabled={toolIds.length >= 10 || tool.validationStatus !== 'valid'}
                    className="text-brand-teal hover:text-brand-teal hover:bg-brand-teal/10"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </div>

          {toolIds.length >= 10 && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                Maximum of 10 tools reached. Remove a tool to add a different one.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AgentToolsTab;
