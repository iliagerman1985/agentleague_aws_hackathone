import { api } from '@/lib/api';
import config from '@/lib/config';

import { type ToolId, type UserId } from '@/types/ids';
import { GameEnvironment } from '@/types/game';

export type ToolValidationStatus = "valid" | "error" | "pending";
// Re-export for backward compatibility
export { GameEnvironment };

export interface Tool {
  id: ToolId;
  userId: UserId | null;
  displayName: string;
  name: string;
  description?: string;
  code: string;
  environment: GameEnvironment;
  validationStatus: ToolValidationStatus;
  createdAt: string;
  updatedAt: string;
  isSystem: boolean;
}

export interface ToolCreate {
  display_name: string;
  description?: string;
  code: string;
  environment: GameEnvironment;
}

export interface ToolUpdate {
  display_name?: string;
  description?: string;
  code?: string;
  environment?: GameEnvironment;
}

// Vibe Chat types removed - use toolAgentService instead

export const toolsService = {
  async list(environment?: GameEnvironment): Promise<Tool[]> {
    const params = environment ? { environment } : undefined;
    return api.tools.list(params);
  },

  async get(id: ToolId): Promise<Tool | null> {
    try {
      return await api.tools.get(id);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async create(data: ToolCreate): Promise<Tool> {
    return api.tools.create(data);
  },

  async update(id: ToolId, data: ToolUpdate): Promise<Tool> {
    return api.tools.update(id, data);
  },

  async clone(id: ToolId): Promise<Tool> {
    return api.tools.clone(id);
  },

  async usage(id: ToolId): Promise<{ agents: { id: string; name: string }[]; agentsCount: number }> {
    return api.tools.usage(id);
  },

  async deleteWithDetach(id: ToolId): Promise<void> {
    return api.tools.delete(id, { detach_from_agents: true });
  },


  async delete(id: ToolId): Promise<void> {
    return api.tools.delete(id);
  },

  async getValidationStatus(id: ToolId): Promise<{ toolId: ToolId; validationStatus: ToolValidationStatus; updatedAt: string; }> {
    return fetchFromApi(`/api/v1/tools/${id}/validation-status`, { method: 'GET' });
  },

  async setValidationStatus(id: ToolId, validationStatus: ToolValidationStatus): Promise<{ toolId: ToolId; validationStatus: ToolValidationStatus; updatedAt: string; }> {
    return fetchFromApi(`/api/v1/tools/${id}/validation-status`, {
      method: 'PUT',
      body: JSON.stringify({ validation_status: validationStatus }),
    });
  },
};

// Helper function for API calls that need custom handling (like streaming)
const fetchFromApi = async (endpoint: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${config.apiUrl}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = errorData.detail;
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
    } catch (parseError) {
      console.warn('Could not parse error response:', parseError);
    }

    if (response.status === 401) {
      window.location.href = '/login';
      throw new Error('Authentication required');
    }

    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return null;
  }

  return await response.json();
};

