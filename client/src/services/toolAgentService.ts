/**
 * Tool creation agent service using Strands
 */

import api from "@/lib/api";
import config from "@/lib/config";
import type { LLMIntegrationId } from "@/types/ids";
import { GameEnvironment } from "@/types/game";

// Re-export for backward compatibility
export { GameEnvironment };

export interface ToolArtifact {
  // Prefer camelCase for client
  toolId?: string;
  displayName?: string;
  name?: string;
  description?: string;  // For compatibility with frontend
  explanation?: string;  // Backend CodeArtifact uses this field
  code?: string;
  validationStatus?: string;
  // Back-compat with streamed chunks or legacy shapes
  tool_id?: string;
  display_name?: string;
  validation_status?: string;
}

export interface TestArtifact {
  scenario_id?: string;
  name?: string;
  description?: string;
  game_state?: Record<string, any>;
  environment?: string;
}

export interface AgentMessage {
  writer: "human" | "agent";
  content?: string;
  tool_artifact?: ToolArtifact;
  test_artifact?: TestArtifact;
  timestamp: string;
}

export interface ToolAgentChatRequest {
  message: string;
  conversation_history: Array<Record<string, any>>;
  integration_id: LLMIntegrationId;
  model_id?: string;
  environment?: GameEnvironment;
  current_tool_code?: string;
  current_test_state?: Record<string, any>;
}

export interface ToolAgentChatResponse {
  content: string;
  tool_artifact?: ToolArtifact;
  test_artifact?: TestArtifact;
  model_used: string;
  should_summarize: boolean;
}

export interface ToolAgentStreamChunk {
  type: "content" | "tool" | "test" | "done" | "error";
  content?: string;
  tool_artifact?: ToolArtifact;
  test_artifact?: TestArtifact;
  is_complete: boolean;
  should_summarize?: boolean;
  error?: string;
}

export interface EnvironmentContext {
  environment: string;
  state_schema: Record<string, any>;
  player_view_schema: Record<string, any>;
  examples: Array<{
    name: string;
    display_name: string;
    description: string;
    code: string;
  }>;
  constraints: string[];
  best_practices: string[];
}

class ToolAgentService {
  /**
   * Send a message to the tool creation agent (non-streaming)
   */
  async chat(request: ToolAgentChatRequest): Promise<ToolAgentChatResponse> {
    return api.post("/api/v1/tool-agent/chat", request);
  }

  /**
   * Stream a conversation with the tool creation agent
   */
  async *streamChat(
    request: ToolAgentChatRequest
  ): AsyncGenerator<ToolAgentStreamChunk, void, unknown> {
    const response = await fetch(
      `${config.apiUrl}/api/v1/tool-agent/chat/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim()) {
            try {
              const chunk = JSON.parse(line) as ToolAgentStreamChunk;
              yield chunk;
            } catch (e) {
              console.error("Failed to parse chunk:", line, e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Get environment context for tool creation
   */
  async getEnvironmentContext(
    environment: GameEnvironment
  ): Promise<EnvironmentContext> {
    return api.get(`/api/v1/tool-agent/context/${environment}`);
  }
}

export const toolAgentService = new ToolAgentService();

