import { api, LLMProvider } from '@/lib/api';
import { type AgentId, type AgentVersionId, type ToolId, type TestScenarioId, type AgentStatisticsId, UserId } from '@/types/ids';
import { GameEnvironment } from '@/types/game';
import { getAvailableGames } from '@/config/gameConfig';

// Re-export for backward compatibility
export { GameEnvironment };

export interface GameEnvironmentMetadata {
  displayName: string;
  description: string;
  maxPlayers: number;
  minPlayers: number;
  supportsSpectators: boolean;
  hasBetting: boolean;
  isTurnBased: boolean;
  allowAutoReenter: boolean;
}

// Agent Base Types
export interface AgentBase {
  name: string;
  description?: string;
  gameEnvironment: GameEnvironment;
  autoBuy: boolean;
  autoReenter: boolean;
  isActive: boolean;
}

export interface AgentCreate extends AgentBase { }

export interface AgentUpdate {
  name?: string;
  description?: string;
  // game_environment is immutable after creation
  autoBuy?: boolean;
  autoReenter?: boolean;
  isActive?: boolean;
}

export interface AgentResponse extends AgentBase {
  id: AgentId;
  userId: UserId | null;
  createdAt: string;
  updatedAt: string;
  // Soft archive fields
  isArchived: boolean;
  archivedAt?: string | null;
  // System agent flag
  isSystem: boolean;
  // Avatar fields
  avatarUrl?: string | null;
  avatarType?: 'default' | 'google' | 'uploaded';
}

export interface AgentFullDetailsResponse extends AgentResponse {
  activeVersion: AgentVersionResponse | null;
  totalVersions: number;
}

// Agent Version Types
export interface AgentVersionDefiningFields {
  systemPrompt: string;
  conversationInstructions?: string;
  exitCriteria?: string;
  toolIds: ToolId[];
}

export interface AgentVersionConfigurationFields {
  slowLlmProvider: LLMProvider;
  fastLlmProvider: LLMProvider;
  slowLlmModel?: string | null;
  fastLlmModel?: string | null;
  timeout: number;
  maxIterations: number;
}

export interface AgentVersionBase extends AgentVersionDefiningFields, AgentVersionConfigurationFields { }

export interface AgentVersionCreate extends AgentVersionBase { }

export interface AgentVersionUpdate {
  // Version-defining fields (changes trigger new version)
  systemPrompt?: string;
  conversationInstructions?: string;
  exitCriteria?: string;
  toolIds?: ToolId[];

  // Configuration fields (changes update current version)
  slowLlmProvider?: LLMProvider;
  fastLlmProvider?: LLMProvider;
  slowLlmModel?: string | null;
  fastLlmModel?: string | null;
  timeout?: number;
  maxIterations?: number;
}

export interface AgentVersionResponse extends AgentVersionBase {
  id: AgentVersionId;
  agentId: AgentId;
  versionNumber: number;
  isActive: boolean;
  createdAt: string;
}

// Test Scenario Types
export interface TestScenarioBase {
  name: string;
  description?: string;
  environment: GameEnvironment;
  gameState: Record<string, any>;
  tags: string[];
}

export interface TestScenarioCreate extends TestScenarioBase { }

export interface TestScenarioUpdate {
  name?: string;
  description?: string;
  gameState?: Record<string, any>;
  tags?: string[];
}

export interface TestScenarioResponse extends TestScenarioBase {
  id: TestScenarioId;
  userId: UserId | null;
  createdAt: string;
  updatedAt: string;
  isSystem: boolean;
}

// Game State Management Types
export interface SaveGameStateRequest {
  name: string;
  description?: string;
  gameState: Record<string, any>;
  tags: string[];
}

export interface SavedGameStatesParams {
  tags?: string[];
  skip?: number;
  limit?: number;
}

// Agent Statistics Types
export interface BestHandInfo {
  value: number;
  description: string;
  potSize: number;
}

export interface PokerSpecificData {
  bestHand: BestHandInfo;
  averagePotWon: number;
  biggestBluffWon: number;
  foldPercentage: number;
  aggressionFactor: number;
  vpip: number;
  totalHandsPlayed: number;
  handsWon: number;
  handsFolded: number;
  totalRaises: number;
  totalCalls: number;
}

export interface AgentGameRating {
  rating: number;
  gamesPlayed: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  highestRating: number;
  lowestRating: number;
}

export interface RecentGameEntry {
  gameId?: string | null;
  gameType: string;
  result: 'win' | 'loss' | 'draw';
  ratingChange: number;
  ratingAfter: number;
}

export interface AgentStatisticsData {
  gamesPlayed: number;
  totalWinnings: number;
  totalLosses: number;
  netBalance: number;
  winRate: number;
  gamesWon: number;
  gamesLost: number;
  gamesDrawn: number;
  sessionTimeSeconds: number;
  longestGameSeconds: number;
  shortestGameSeconds: number | null;
  gameRatings: Record<string, AgentGameRating>;
  recentForm: RecentGameEntry[];
  environmentSpecificData: {
    poker?: PokerSpecificData;
  };
  customMetrics: Record<string, any>;
}

export interface AgentStatisticsResponse {
  id: AgentStatisticsId;
  agentId: AgentId;
  statistics: AgentStatisticsData;
  lastUpdated: string;
  updatedAt?: string;
}

// Agent Test Response - for /api/v1/agents/{id}/test endpoint
export interface AgentTestResponse {
  reasoning: string;
  action?: any; // TexasHoldemMove or null
  toolRequest?: {
    toolId: ToolId;
    toolName: string;
    parameters: Record<string, any>;
  } | null;
  validationErrors: string[];
  executionTimeMs: number;
  modelUsed: string;
  isFinal: boolean;
  inputTokens?: number | null;
  outputTokens?: number | null;
  totalTokens?: number | null;
  costUsd?: number | null;
}

// Version Management Types
export interface AgentVersionComparisonResponse {
  version1: AgentVersionResponse;
  version2: AgentVersionResponse;
  differences: AgentVersionDifference[];
}

export interface AgentVersionDifference {
  field: string;
  version1Value: any;
  version2Value: any;
  changeType: 'added' | 'removed' | 'modified';
}

export interface AgentVersionLimitInfo {
  currentVersionCount: number;
  maxVersions: number;
  canCreateNewVersion: boolean;
  oldestVersionNumber?: number | null;
  latestVersionNumber?: number | null;
  activeVersionNumber?: number | null;
}

export interface AgentVersionRollbackRequest {
  targetVersionId: AgentVersionId;
}

// Environment Schema Types
export interface VariableInfo {
  name: string;
  type: string;
  description: string;
  exampleValue: any;
  path: string;
}

export interface EnvironmentSchemaResponse {
  environment: GameEnvironment;
  variables: VariableInfo[];
  inputSchema: Record<string, any>;
  outputSchema: Record<string, any>;
}

// Autocomplete Types
export interface AutocompleteResponse {
  suggestions: string[];
  prefix: string;
}

// Prompt Validation Types
export interface PromptValidationRequest {
  prompt: string;
  environment: GameEnvironment;
}

export interface PromptValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  variableReferences: string[];
}

// Agent Service Implementation

// In-memory cache for avatars by agentVersionId
const _avatarCache: Map<string, { avatarUrl?: string | null; avatarType?: string; agentId?: AgentId }> = new Map();

export const agentsService = {
  // Agent CRUD Operations
  async list(gameEnvironment?: GameEnvironment): Promise<AgentResponse[]> {
    const params = gameEnvironment ? { game_environment: gameEnvironment } : undefined;
    return api.agents.list(params);
  },

  async get(id: AgentId): Promise<AgentResponse | null> {
    try {
      return await api.agents.get(id);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async create(data: AgentCreate): Promise<AgentResponse> {
    return api.agents.create(data);
  },

  async update(id: AgentId, data: AgentUpdate): Promise<AgentResponse> {
    return api.agents.update(id, data);
  },

  async delete(id: AgentId): Promise<void> {
    return api.agents.delete(id);
  },

  async clone(id: AgentId): Promise<AgentResponse> {
    return api.agents.clone(id);
  },

  // Agent Version Operations
  async getVersions(agentId: AgentId): Promise<AgentVersionResponse[]> {
    return api.agents.getVersions(agentId);
  },

  async getVersion(agentId: AgentId, versionId: AgentVersionId): Promise<AgentVersionResponse | null> {
    try {
      return await api.agents.getVersion(agentId, versionId);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async getActiveVersion(agentId: AgentId): Promise<AgentVersionResponse | null> {
    try {
      return await api.agents.getActiveVersion(agentId);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async activateVersion(agentId: AgentId, versionId: AgentVersionId): Promise<AgentVersionResponse> {
    return api.agents.activateVersion(agentId, versionId);
  },

  async createVersion(agentId: AgentId, data: AgentVersionCreate): Promise<AgentVersionResponse> {
    // Map camelCase to snake_case for backend
    const wire: any = {
      system_prompt: data.systemPrompt,
      conversation_instructions: data.conversationInstructions,
      exit_criteria: data.exitCriteria,
      tool_ids: data.toolIds,
      slow_llm_provider: data.slowLlmProvider,
      fast_llm_provider: data.fastLlmProvider,
      slow_llm_model: data.slowLlmModel,
      fast_llm_model: data.fastLlmModel,
      timeout: data.timeout,
      max_iterations: data.maxIterations,
    };
    return api.agents.createVersion(agentId, wire);
  },

  async updateVersion(agentId: AgentId, versionId: AgentVersionId, data: AgentVersionUpdate): Promise<AgentVersionResponse> {
    // Map camelCase to snake_case for backend
    const wire: any = {};
    if (data.systemPrompt !== undefined) wire.system_prompt = data.systemPrompt;
    if (data.conversationInstructions !== undefined) wire.conversation_instructions = data.conversationInstructions;
    if (data.exitCriteria !== undefined) wire.exit_criteria = data.exitCriteria;
    if (data.toolIds !== undefined) wire.tool_ids = data.toolIds;
    if (data.slowLlmProvider !== undefined) wire.slow_llm_provider = data.slowLlmProvider;
    if (data.fastLlmProvider !== undefined) wire.fast_llm_provider = data.fastLlmProvider;
    if (data.slowLlmModel !== undefined) wire.slow_llm_model = data.slowLlmModel;
    if (data.fastLlmModel !== undefined) wire.fast_llm_model = data.fastLlmModel;
    if (data.timeout !== undefined) wire.timeout = data.timeout;
    if (data.maxIterations !== undefined) wire.max_iterations = data.maxIterations;
    return api.agents.updateVersion(agentId, versionId, wire);
  },

  async rollbackVersion(agentId: AgentId, data: AgentVersionRollbackRequest): Promise<AgentVersionResponse> {
    return api.agents.rollbackVersion(agentId, data);
  },

  async compareVersions(agentId: AgentId, version1Id: AgentVersionId, version2Id: AgentVersionId): Promise<AgentVersionComparisonResponse> {
    return api.agents.compareVersions(agentId, {
      version_1_id: version1Id,
      version_2_id: version2Id,
    });
  },

  async getVersionLimitInfo(agentId: AgentId): Promise<AgentVersionLimitInfo> {
    return api.agents.getVersionLimitInfo(agentId);
  },

  // Agent Statistics
  async getStatistics(agentId: AgentId): Promise<AgentStatisticsResponse | null> {
    try {
      return await api.agents.getStatistics(agentId);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async updateStatistics(agentId: AgentId, updates: Record<string, any>): Promise<AgentStatisticsResponse> {
    return api.agents.updateStatistics(agentId, updates);
  },


  async validateResponse(agentId: AgentId, response: any, environment: GameEnvironment, gameState: Record<string, any>): Promise<{ valid: boolean; errors?: string[]; suggestions?: string[] }> {
    return api.agents.validateResponse(agentId, {
      response,
      environment,
      game_state: gameState,
    });
  },

  // Test Scenario Operations
  async testAgent(
    agentId: AgentId,
    data: {
      game_state: Record<string, any>;
      llm_integration_id: string;
      tool_result?: any;
      iteration_history?: any[];
      max_iterations?: number;
      max_retries?: number;
    }
  ): Promise<AgentTestResponse> {
    return api.agents.testAgent(agentId as unknown as string, data);
  },

  async getTestScenarios(options?: { agentId?: AgentId; includeSystem?: boolean }): Promise<TestScenarioResponse[]> {
    const params: Record<string, any> = {};
    if (options?.agentId) {
      params.agentId = options.agentId;
    }
    if (options?.includeSystem !== undefined) {
      params.include_system = options.includeSystem;
    }
    return api.agents.getTestScenarios(Object.keys(params).length > 0 ? params : undefined);
  },

  async getTestScenario(id: TestScenarioId): Promise<TestScenarioResponse | null> {
    try {
      return await api.agents.getTestScenario(id);
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  },

  async createTestScenario(data: TestScenarioCreate): Promise<TestScenarioResponse> {
    return api.agents.createTestScenario(data);
  },

  async updateTestScenario(id: TestScenarioId, data: TestScenarioUpdate): Promise<TestScenarioResponse> {
    return api.agents.updateTestScenario(id, data);
  },

  async deleteTestScenario(id: TestScenarioId): Promise<void> {
    return api.agents.deleteTestScenario(id);
  },

  // Environment Schema Operations
  async getEnvironmentSchema(environment: GameEnvironment): Promise<EnvironmentSchemaResponse> {
    const serverResp = await api.agents.getEnvironmentSchema(environment);
    // serverResp.variables is a map: { path: { type, description, example } }
    const variables: VariableInfo[] = Object.entries(serverResp.variables || {}).map(([path, v]: [string, any]) => ({
      name: path,
      path,
      type: String(v.type ?? "unknown"),
      description: String(v.description ?? ""),
      exampleValue: v.example,
    }));
    return {
      environment: environment,
      variables,
      inputSchema: serverResp.input_schema ?? {},
      outputSchema: serverResp.output_schema ?? {},
    };
  },

  async getAutocomplete(environment: GameEnvironment, prefix: string): Promise<AutocompleteResponse> {
    // Not used; client-side autocomplete preferred. Keep for compatibility.
    const resp = await api.agents.getAutocomplete(environment, { prefix });
    return { suggestions: (resp || []).map((r: any) => r.path), prefix };
  },

  async validatePrompt(data: PromptValidationRequest): Promise<PromptValidationResponse> {
    return api.agents.validatePrompt(data);
  },

  // Synthetic Data Generation
  async generateTestData(instructions: string, environment: GameEnvironment): Promise<Record<string, any>> {
    return api.agents.generateTestData({
      instructions,
      environment,
    });
  },

  async saveTestScenario(data: TestScenarioCreate): Promise<TestScenarioResponse> {
    return api.agents.saveTestScenario(data);
  },

  // Agent Version to Agent lookup utilities
  async getAgentFromVersion(agentVersionId: AgentVersionId): Promise<AgentResponse | null> {
    try {
      // Resolve agentId from agent_version_id (publicly accessible)
      const response = await api.get(`/api/v1/agent-versions/${agentVersionId}/agent`);
      const agentId = response?.agentId as string | undefined;
      if (!agentId) {
        console.warn(`Agent version ${agentVersionId} returned no agentId`, response);
        return null;
      }

      // Prefer the public profile endpoint to ensure avatar fields are present even for non-owned agents
      try {
        const profile: any = await api.get(`/api/v1/public/agents/${agentId}/profile`, { timeout: 20000 });
        const agentCore = profile?.agent ?? profile;
        return agentCore as AgentResponse;
      } catch (profileErr: any) {
        // Fallback to the generic public agent endpoint
        try {
          const agent = await api.get(`/api/v1/public/agents/${agentId}`);
          return agent as AgentResponse;
        } catch (fallbackErr: any) {
          console.warn(`Could not get public agent details for ${agentId}:`, fallbackErr);
          return null;
        }
      }
    } catch (error) {
      console.error("Failed to get agent from version", agentVersionId, error);
      return null;
    }
  },

  async getAgentAvatarsFromVersionIds(agentVersionIds: AgentVersionId[]): Promise<Record<string, { avatarUrl?: string | null; avatarType?: string }>> {
    console.log('[agentsService] Fetching avatars for version IDs:', agentVersionIds);

    const avatarMap: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};

    // Fetch all avatars in parallel
    await Promise.all(
      agentVersionIds.map(async (versionId) => {
        try {
          const agent = await this.getAgentFromVersion(versionId);
          if (agent && agent.avatarUrl) {
            avatarMap[versionId] = {
              avatarUrl: agent.avatarUrl,
              avatarType: agent.avatarType ?? 'default',
            };
            console.log(`[agentsService] Loaded avatar for version ${versionId}:`, agent.avatarUrl);
          } else {
            console.warn(`[agentsService] No avatar found for version ${versionId}`);
          }
        } catch (error) {
          console.warn(`[agentsService] Failed to load avatar for version ${versionId}:`, error);
        }
      })
    );

    console.log('[agentsService] Final avatar map:', avatarMap);
    return avatarMap;
  },

  async getAgentAvatarsFromVersionIdsBatch(agentVersionIds: AgentVersionId[]): Promise<Record<string, { avatarUrl?: string | null; avatarType?: string }>> {
    const uniqueIds = Array.from(new Set(agentVersionIds.map(String)));
    const result: Record<string, { avatarUrl?: string | null; avatarType?: string }> = {};

    // Serve from cache first
    const missing: string[] = [];
    for (const id of uniqueIds) {
      const cached = _avatarCache.get(id);
      if (cached) {
        result[id] = { avatarUrl: cached.avatarUrl, avatarType: cached.avatarType };
      } else {
        missing.push(id);
      }
    }
    if (missing.length === 0) return result;

    try {
      const resp = await api.post('/api/v1/public/agent-avatars-by-version', {
        agent_version_ids: missing,
      }, { timeout: 20000 });
      const list = Array.isArray(resp?.avatars) ? resp.avatars as Array<{ agentVersionId: string; agentId: string; avatarUrl?: string | null; avatarType?: string }> : [];
      for (const item of list) {
        const key = String(item.agentVersionId);
        _avatarCache.set(key, { avatarUrl: item.avatarUrl ?? null, avatarType: item.avatarType ?? 'default', agentId: item.agentId as unknown as AgentId });
        result[key] = { avatarUrl: item.avatarUrl ?? null, avatarType: item.avatarType ?? 'default' };
      }
    } catch (e) {
      console.warn('[agentsService] Batch avatar fetch failed, falling back per-version:', e);
      // Fallback: per-version (slower)
      await Promise.all(missing.map(async (versionId) => {
        try {
          const agent = await this.getAgentFromVersion(versionId as unknown as AgentVersionId);
          if (agent) {
            const data = { avatarUrl: agent.avatarUrl ?? null, avatarType: agent.avatarType ?? 'default' };
            _avatarCache.set(String(versionId), { ...data, agentId: agent.id });
            result[String(versionId)] = data;
          }
        } catch (err) {
          console.warn('[agentsService] Fallback avatar fetch failed for', versionId, err);
        }
      }));
    }
    return result;
  },

  async getAgentIdsFromVersionIdsBatch(agentVersionIds: AgentVersionId[]): Promise<Record<string, AgentId>> {
    const uniqueIds = Array.from(new Set(agentVersionIds.map(String)));
    const result: Record<string, AgentId> = {} as any;
    const missing: string[] = [];
    for (const id of uniqueIds) {
      const cached = _avatarCache.get(id);
      if (cached?.agentId) {
        result[id] = cached.agentId;
      } else {
        missing.push(id);
      }
    }
    if (missing.length === 0) return result;

    try {
      const resp = await api.post('/api/v1/public/agent-avatars-by-version', {
        agent_version_ids: missing,
      }, { timeout: 20000 });
      const list = Array.isArray(resp?.avatars) ? resp.avatars as Array<{ agentVersionId: string; agentId: string; avatarUrl?: string | null; avatarType?: string }> : [];
      for (const item of list) {
        const key = String(item.agentVersionId);
        const cached = _avatarCache.get(key) || {};
        _avatarCache.set(key, { ...cached, agentId: item.agentId as unknown as AgentId, avatarUrl: cached.avatarUrl ?? item.avatarUrl ?? null, avatarType: cached.avatarType ?? item.avatarType ?? 'default' });
        result[key] = item.agentId as unknown as AgentId;
      }
    } catch (e) {
      console.warn('[agentsService] Batch agent-id fetch failed, falling back per-version:', e);
      await Promise.all(missing.map(async (versionId) => {
        try {
          const agent = await this.getAgentFromVersion(versionId as unknown as AgentVersionId);
          if (agent?.id) {
            const cached = _avatarCache.get(String(versionId)) || {};
            _avatarCache.set(String(versionId), { ...cached, agentId: agent.id, avatarUrl: cached.avatarUrl ?? agent.avatarUrl ?? null, avatarType: cached.avatarType ?? agent.avatarType ?? 'default' });
            result[String(versionId)] = agent.id;
          }
        } catch (err) {
          console.warn('[agentsService] Fallback agent-id fetch failed for', versionId, err);
        }
      }));
    }
    return result;
  },

  async getAgentProfile(agentId: AgentId): Promise<any> {
    try {
      // Try authenticated endpoint first (for user's own agents)
      const profile = await api.get(`/api/v1/agents/${agentId}/profile`, { timeout: 20000 });
      return profile;
    } catch (authError: any) {
      // If authenticated fetch fails (likely not owner), try public endpoint
      try {
        const publicProfile = await api.get(`/api/v1/public/agents/${agentId}/profile`, { timeout: 20000 });
        return publicProfile;
      } catch (publicError: any) {
        throw authError;
      }
    }
  },

    async getAgentGames(agentId: AgentId, limit: number = 50, offset: number = 0): Promise < any[] > {
      return api.get(`/api/v1/agents/${agentId}/games?limit=${limit}&offset=${offset}`);
    },
};

// Game Environment Metadata
let _envMetadataCache: Record<GameEnvironment, GameEnvironmentMetadata> | null = null;

export async function loadGameEnvironmentMetadata(): Promise<Record<GameEnvironment, GameEnvironmentMetadata>> {
  if (_envMetadataCache) return _envMetadataCache;
  const list = await api.agents.listEnvironments();
  const typed: Record<GameEnvironment, GameEnvironmentMetadata> = {} as Record<GameEnvironment, GameEnvironmentMetadata>;
  for (const item of list) {
    const env = item.id as unknown as GameEnvironment;
    typed[env] = item.metadata as GameEnvironmentMetadata;
  }
  _envMetadataCache = typed;
  return typed;
}

export function getGameEnvironmentMetadata(environment: GameEnvironment): GameEnvironmentMetadata {
  if (_envMetadataCache && _envMetadataCache[environment]) {
    return _envMetadataCache[environment];
  }
  // Fallback: humanize the enum for display and default other fields
  const humanized = String(environment).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Set default values for auto re-enter based on environment
  const defaultAutoReenter = environment === GameEnvironment.TEXAS_HOLDEM;

  return {
    displayName: humanized,
    description: "",
    maxPlayers: 0,
    minPlayers: 0,
    supportsSpectators: false,
    hasBetting: false,
    isTurnBased: true,
    allowAutoReenter: defaultAutoReenter,
  };
}

export function getCachedGameEnvironmentMetadata(): Record<GameEnvironment, GameEnvironmentMetadata> | null {
  return _envMetadataCache;
}

export function getAvailableGameEnvironments(): GameEnvironment[] {
  // Get available games from game config
  const availableGames = getAvailableGames();
  const availableGameIds = new Set(availableGames.map(game => game.id));

  return Object.values(GameEnvironment).filter(env => availableGameIds.has(env));
}
