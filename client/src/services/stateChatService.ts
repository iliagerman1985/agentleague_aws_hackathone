import { type LLMIntegrationId } from '@/types/ids';
import config from '@/lib/config';

export interface StateChatMessage {
  writer: 'human' | 'llm';
  content: string;
}

export interface StateChatRequest {
  message: string;
  conversation_history: StateChatMessage[];
  llm_integration_id: LLMIntegrationId;
  model_id?: string | null;
  current_state?: Record<string, any> | null;
}

export interface StateChatFinalPayload {
  state: Record<string, any>;
  description: string;
  message: string;
}

export type StateChatStreamChunk =
  | { type: 'content'; content?: string }
  | { type: 'done'; final: StateChatFinalPayload; is_complete?: boolean }
  | { type: 'error'; error: string; is_complete?: boolean };

export async function* streamStateChat(agentId: string, request: StateChatRequest): AsyncGenerator<StateChatStreamChunk, void, unknown> {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // Debug: request start
  try {
    console.debug('[StateChatService] POST /state-chat/stream', {
      url: `${config.apiUrl}/api/v1/agents/${agentId}/state-chat/stream`,
      integration: request.llm_integration_id,
      hasHistory: request.conversation_history?.length > 0,
      hasCurrentState: !!request.current_state,
    });
  } catch {}

  const response = await fetch(`${config.apiUrl}/api/v1/agents/${agentId}/state-chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
  try { console.debug('[StateChatService] response', { status: response.status }); } catch {}

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      errorMessage = data?.detail || data?.message || errorMessage;
    } catch {
      // ignore parse error
    }
    if (response.status === 401) {
      window.location.href = '/login';
      throw new Error('Authentication required');
    }
    throw new Error(errorMessage);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body reader available');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Flush any leftover buffer (in case the final line lacked a trailing \n)
        const tail = (buffer || '').trim();
        if (tail) {
          try {
            const chunk = JSON.parse(tail) as StateChatStreamChunk;
            try {
              console.debug('[StateChatService] tail chunk', {
                type: (chunk as any).type,
                hasFinal: !!(chunk as any).final,
                is_complete: !!(chunk as any).is_complete,
              });
            } catch {}
            yield chunk;
          } catch (e) {
            console.warn('Failed to parse tail state-chat chunk', e, tail);
          }
        }
        try { console.debug('[StateChatService] stream closed'); } catch {}
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const chunk = JSON.parse(line) as StateChatStreamChunk;
          try {
            console.debug('[StateChatService] chunk', {
              type: (chunk as any).type,
              contentLen: (chunk as any).content ? (chunk as any).content.length : 0,
              hasFinal: !!(chunk as any).final,
              is_complete: !!(chunk as any).is_complete,
            });
          } catch {}
          yield chunk;
          // Stop if server signals completion
          if ((chunk as any).type === 'done' || (chunk as any).is_complete) {
            try { console.debug('[StateChatService] complete'); } catch {}
            return;
          }
        } catch (e) {
          // Non-fatal: skip malformed line
          console.warn('Failed to parse state-chat chunk', e, line);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}



export async function fetchStateChatExamples(agentId: string): Promise<string[]> {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${config.apiUrl}/api/v1/agents/${agentId}/state-chat/examples`, { headers });
  if (!res.ok) return [];
  try {
    const data = await res.json();
    return Array.isArray(data?.examples) ? data.examples : [];
  } catch {
    return [];
  }
}
