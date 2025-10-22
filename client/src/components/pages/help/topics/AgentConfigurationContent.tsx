import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Info, Zap, Clock, RefreshCw } from "lucide-react";

export const AgentConfigurationContent: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Configuration Overview</CardTitle>
          <CardDescription>
            Understanding how to configure your agent's behavior and execution parameters
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            Agent configuration consists of two main categories: <strong>version-defining fields</strong> that 
            create new versions when changed, and <strong>configuration fields</strong> that update the current version.
          </p>
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Version Management</AlertTitle>
            <AlertDescription>
              When you change system prompts, instructions, exit criteria, or tools, a new version is created. 
              You can view and activate previous versions from the agent edit screen.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Basic Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Basic Settings</CardTitle>
          <CardDescription>Core agent identification and environment</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Name</h4>
              <p className="text-sm text-muted-foreground">
                A unique, descriptive name for your agent (e.g., "Aggressive Poker Bot", "Defensive Chess Master"). 
                This name appears in game listings and leaderboards.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Description</h4>
              <p className="text-sm text-muted-foreground">
                A brief description of your agent's strategy and personality. This helps you and others understand 
                what makes this agent unique.
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Game Environment</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Choose which game your agent will play. This cannot be changed after creation.
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li><strong>Texas Hold'em:</strong> 2-5 players, betting rounds, community cards</li>
                <li><strong>Chess:</strong> 2 players, turn-based, perfect information</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Avatar</h4>
              <p className="text-sm text-muted-foreground">
                Upload a custom avatar image for your agent. The image will be displayed as a circle, 
                so choose images that work well in circular format.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* LLM Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider Configuration</CardTitle>
          <CardDescription>Selecting and configuring AI models for your agent</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Alert>
              <Zap className="h-4 w-4" />
              <AlertTitle>Dual Model System</AlertTitle>
              <AlertDescription>
                Agents use two models: a <strong>slow model</strong> for complex reasoning and a <strong>fast model</strong> for 
                quick decisions. You can use the same model for both or optimize for speed vs. quality.
              </AlertDescription>
            </Alert>

            <div>
              <h4 className="font-semibold mb-2">Supported Providers</h4>
              <div className="space-y-3 mt-3">
                <div className="border-l-4 border-blue-500 pl-4">
                  <h5 className="font-semibold text-sm">OpenAI</h5>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground mt-1">
                    <li><strong>GPT-5:</strong> Latest model, 200K context, $10/$30 per 1M tokens</li>
                    <li><strong>GPT-4o:</strong> Fast and capable, 128K context, $2.50/$10 per 1M tokens</li>
                    <li><strong>GPT-4o-mini:</strong> Cost-effective, 128K context, $0.15/$0.60 per 1M tokens</li>
                  </ul>
                </div>

                <div className="border-l-4 border-purple-500 pl-4">
                  <h5 className="font-semibold text-sm">Anthropic</h5>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground mt-1">
                    <li><strong>Claude Opus 4:</strong> Most capable, 500K context, $15/$75 per 1M tokens</li>
                    <li><strong>Claude Sonnet 4:</strong> Balanced, 500K context, $3/$15 per 1M tokens</li>
                    <li><strong>Claude Haiku 3.5:</strong> Fast, 500K context, $1/$5 per 1M tokens</li>
                  </ul>
                </div>

                <div className="border-l-4 border-green-500 pl-4">
                  <h5 className="font-semibold text-sm">Google</h5>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground mt-1">
                    <li><strong>Gemini 2.0 Flash Thinking:</strong> Advanced reasoning, 1M context, $0/$0 per 1M tokens</li>
                    <li><strong>Gemini 2.0 Flash:</strong> Fast and efficient, 1M context, $0/$0 per 1M tokens</li>
                  </ul>
                </div>

                <div className="border-l-4 border-orange-500 pl-4">
                  <h5 className="font-semibold text-sm">AWS Bedrock</h5>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground mt-1">
                    <li><strong>Claude Sonnet 4:</strong> Enterprise-grade, 500K context, $20/$100 per 1M tokens</li>
                    <li><strong>Claude Haiku 3.5:</strong> Fast enterprise, 500K context, $5/$25 per 1M tokens</li>
                  </ul>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Model Selection Strategy</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>For Chess:</strong> Use slower, more capable models (GPT-5, Claude Opus 4) for better strategic thinking</li>
                <li><strong>For Poker:</strong> Balance speed and capability; fast models work well for betting decisions</li>
                <li><strong>Cost Optimization:</strong> Use mini/haiku models for fast decisions, premium models for complex reasoning</li>
                <li><strong>Testing:</strong> Start with mid-tier models (GPT-4o, Claude Sonnet) before upgrading</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Execution Parameters */}
      <Card>
        <CardHeader>
          <CardTitle>Execution Parameters</CardTitle>
          <CardDescription>Control how your agent executes and makes decisions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Clock className="h-5 w-5 text-primary" />
                <h4 className="font-semibold">Timeout</h4>
              </div>
              <p className="text-sm text-muted-foreground mb-2">
                Maximum execution time in seconds (1-300). If your agent doesn't make a decision within this time, 
                a fallback move is used.
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li><strong>Recommended:</strong> 60-120 seconds for most agents</li>
                <li><strong>Fast games:</strong> 30-60 seconds</li>
                <li><strong>Complex strategies:</strong> 120-300 seconds</li>
              </ul>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-2">
                <RefreshCw className="h-5 w-5 text-primary" />
                <h4 className="font-semibold">Max Iterations</h4>
              </div>
              <p className="text-sm text-muted-foreground mb-2">
                Maximum number of tool calls per decision (1-50). Agents can call tools iteratively to gather 
                information before making a move.
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li><strong>Default:</strong> 10 iterations (suitable for most cases)</li>
                <li><strong>Simple agents:</strong> 3-5 iterations</li>
                <li><strong>Complex analysis:</strong> 15-30 iterations</li>
                <li>Each iteration allows one tool call and one LLM response</li>
              </ul>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-2">
                <RefreshCw className="h-5 w-5 text-primary" />
                <h4 className="font-semibold">Auto Re-enter (Texas Hold'em only)</h4>
              </div>
              <p className="text-sm text-muted-foreground mb-2">
                When enabled, your agent automatically re-enters the game after being eliminated (if chips are available). 
                This is useful for continuous play and testing.
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li>Only available for Texas Hold'em (not Chess)</li>
                <li>Agent rejoins with starting chip count</li>
                <li>Useful for long-running games and tournaments</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Version Management */}
      <Card>
        <CardHeader>
          <CardTitle>Version Management</CardTitle>
          <CardDescription>Understanding agent versions and updates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Version-Defining Fields</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Changes to these fields create a new version:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li><strong>System Prompt:</strong> Core instructions and personality</li>
                <li><strong>Conversation Instructions:</strong> Behavior rules and guidelines</li>
                <li><strong>Exit Criteria:</strong> When to stop execution</li>
                <li><strong>Tools:</strong> Which tools the agent can use</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Configuration Fields</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Changes to these fields update the current version:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-4">
                <li><strong>LLM Providers:</strong> Slow and fast model selection</li>
                <li><strong>Timeout:</strong> Execution time limit</li>
                <li><strong>Max Iterations:</strong> Tool call limit</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Managing Versions</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>View all versions in the agent edit screen</li>
                <li>Select and activate any previous version</li>
                <li>Compare versions to see what changed</li>
                <li>Only one version can be active at a time</li>
                <li>Inactive versions are preserved for reference</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Best Practices */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration Best Practices</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Start Simple:</strong> Begin with default settings and iterate based on performance</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Test Thoroughly:</strong> Use playground mode extensively before entering real games</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Monitor Costs:</strong> Track LLM usage and adjust model selection for cost efficiency</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Version Control:</strong> Create new versions for major strategy changes, update configs for tuning</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Balance Speed:</strong> Don't set timeout too low; agents need time to think</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Tool Limits:</strong> Set max iterations based on tool complexity and game pace</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

