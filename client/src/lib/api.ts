// API service for making requests to the backend
import config from './config';
import { type LLMIntegrationId, type UserId, type ToolId, type AgentId, type AgentVersionId, type ErrorReportId } from '@/types/ids';

// Get API URL from configuration
const API_URL = config.apiUrl;

let pendingAutoLogin: Promise<boolean> | null = null;

type NormalizedHeaders = Record<string, string>;

const isFormDataBody = (body: RequestInit["body"]): body is FormData => {
  return typeof FormData !== "undefined" && body instanceof FormData;
};

const normalizeHeaders = (incomingHeaders: HeadersInit | undefined): NormalizedHeaders => {
  const headers: NormalizedHeaders = {};

  if (!incomingHeaders) {
    return headers;
  }

  if (incomingHeaders instanceof Headers) {
    incomingHeaders.forEach((value, key) => {
      headers[key] = value;
    });
    return headers;
  }

  if (Array.isArray(incomingHeaders)) {
    for (const [key, value] of incomingHeaders) {
      headers[key] = value;
    }
    return headers;
  }

  return { ...incomingHeaders } as NormalizedHeaders;
};

const findHeaderKey = (headers: NormalizedHeaders, target: string): string | undefined => {
  const targetLower = target.toLowerCase();
  return Object.keys(headers).find((key) => key.toLowerCase() === targetLower);
};

const removeHeader = (headers: NormalizedHeaders, target: string): void => {
  const key = findHeaderKey(headers, target);
  if (key) {
    delete headers[key];
  }
};

const ensureContentType = (headers: NormalizedHeaders, body: RequestInit["body"]): void => {
  const hasContentType = Boolean(findHeaderKey(headers, "Content-Type"));

  if (isFormDataBody(body)) {
    if (hasContentType) {
      removeHeader(headers, "Content-Type");
    }
    return;
  }

  if (!hasContentType && body !== undefined && body !== null) {
    headers["Content-Type"] = "application/json";
  }
};

// Types for authentication
export interface SignUpRequest {
  email: string;
  password: string;
  passwordConfirmation: string;
  firstName: string;
  lastName: string;
}

export interface SignUpResponse {
  message: string;
  userSub: string;
  userConfirmed: boolean;
}

export interface ConfirmSignUpRequest {
  email: string;
  confirmationCode: string;
}

export interface SignInRequest {
  email: string;
  password: string;
}

export interface UserInfo {
  username: string;
  email: string;
  fullName?: string;
  nickname?: string | null;
  displayName?: string | null;
  role: string;
  isActive: boolean;
  coinsBalance?: number;
  userSub?: string;
  avatarUrl?: string | null;
  avatarType?: string | null;
  createdAt?: string;
}



export interface ErrorReportCreateRequest {
  message: string;
  name?: string | null;
  stack?: string | null;
  componentStack?: string | null;
  url?: string | null;
  userAgent?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ErrorReportResponse extends ErrorReportCreateRequest {
  id: ErrorReportId;
  userId: UserId | null;
  userEmail?: string | null;
  userUsername?: string | null;
  userFullName?: string | null;
  userRole?: string | null;
  createdAt: string;
  updatedAt: string;
}

// LLM Integration enums and types
export enum LLMProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  GOOGLE = 'google',
  AWS_BEDROCK = 'aws_bedrock'
}

export interface LLMIntegrationCreate {
  provider: LLMProvider;
  apiKey: string;
  selectedModel: string;
  displayName?: string | null;
  isActive?: boolean;
  isDefault?: boolean;
}

export interface LLMIntegrationUpdate {
  selectedModel?: string;
  displayName?: string;
  isActive?: boolean;
  apiKey?: string;
}

export interface LLMIntegrationResponse {
  id: LLMIntegrationId;
  userId: UserId;
  provider: LLMProvider;
  selectedModel: string;
  displayName?: string;
  isActive: boolean;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface LLMTestRequest {
  testPrompt?: string;
}

export interface LLMTestResponse {
  success: boolean;
  responseText?: string;
  errorMessage?: string;
  latencyMs?: number;
}

export interface ProviderModels {
  [provider: string]: {
    models: string[];
  };
}

// Enhanced model selection types
export interface ModelInfo {
  modelId: string;
  displayName: string;
  description: string;
  contextWindow: number;
  supportsTools: boolean;
  supportsVision: boolean;
  inputPricePer1m: number;
  outputPricePer1m: number;
}

export interface ProviderModelInfo {
  provider: LLMProvider;
  models: ModelInfo[];
}

export interface SelectableModel {
  modelId: string;
  displayName: string;
  provider: LLMProvider;
  providerName: string;
  integrationId: LLMIntegrationId;
  description: string;
  contextWindow: number;
  supportsTools: boolean;
  supportsVision: boolean;
  inputPricePer1m: number;
  outputPricePer1m: number;
}

export interface ModelSelection {
  modelId: string;
  provider: LLMProvider;
  integrationId: LLMIntegrationId;
}

export interface SignInResponse {
  accessToken: string;
  idToken: string;
  refreshToken?: string;
  expiresIn: number;
  tokenType: string;
  user: UserInfo;
}


export interface PasswordChangeRequest {
  oldPassword: string;
  newPassword: string;
}

export interface PasswordChangeResponse {
  message: string;
}

export interface DeleteAccountRequest {
  password: string;
}

export interface DeleteAccountResponse {
  message: string;
  success: boolean;
}


export interface OAuthUrlResponse {
  oauthUrl: string;
  state: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state?: string;
}

/**
 * Get stored auth token
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}



/**
 * Store auth tokens
 */
function storeAuthTokens(tokens: {
  accessToken: string;
  idToken: string;
  refreshToken?: string;
  expiresIn: number;
}) {
  localStorage.setItem('access_token', tokens.accessToken);
  localStorage.setItem('id_token', tokens.idToken);
  if (tokens.refreshToken) {
    localStorage.setItem('refresh_token', tokens.refreshToken);
  }
  // Store expiration time
  const expiresAt = Date.now() + (tokens.expiresIn * 1000);
  localStorage.setItem('token_expires_at', expiresAt.toString());
}

/**
 * Clear stored auth tokens
 */
function clearAuthTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('id_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('token_expires_at');
  localStorage.removeItem('user_info');
}

/**
 * Check if token is expired
 */
function isTokenExpired(): boolean {
  const expiresAt = localStorage.getItem('token_expires_at');
  if (!expiresAt) return true;
  return Date.now() > parseInt(expiresAt);
}

/**
 * Attempt automatic re-login using stored credentials
 */
async function attemptAutoRelogin(): Promise<boolean> {
  if (pendingAutoLogin) {
    return pendingAutoLogin;
  }

  pendingAutoLogin = (async () => {
    try {
      const rememberedEmail = localStorage.getItem('rememberedEmail');
      const rememberedPassword = localStorage.getItem('rememberedPassword');

      if (!rememberedEmail || !rememberedPassword) {
        return false;
      }

      const password = atob(rememberedPassword);

      const response = await fetch(`${API_URL}/api/v1/auth/signin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: rememberedEmail, password }),
      });

      if (response.ok) {
        const data = await response.json();
        storeAuthTokens(data);
        localStorage.setItem("user_info", JSON.stringify(data.user));
        console.log("Auto re-login successful");
        return true;
      }

      console.warn("Auto re-login failed, clearing stored credentials");
      localStorage.removeItem("rememberedEmail");
      localStorage.removeItem("rememberedPassword");
      return false;
    } catch (error) {
      console.warn("Auto re-login failed:", error);
      localStorage.removeItem("rememberedEmail");
      localStorage.removeItem("rememberedPassword");
      return false;
    } finally {
      pendingAutoLogin = null;
    }
  })();

  return pendingAutoLogin;
}

async function ensureFreshToken(): Promise<string | null> {
  const existingToken = getAuthToken();
  if (existingToken && !isTokenExpired()) {
    return existingToken;
  }

  const autoLoginSuccess = await attemptAutoRelogin();
  if (!autoLoginSuccess) {
    return null;
  }

  const refreshedToken = getAuthToken();
  if (!refreshedToken || isTokenExpired()) {
    return null;
  }

  return refreshedToken;
}

/**
 * Fetch data from the API with error handling and auth
 */
async function fetchFromApi(endpoint: string, options: RequestInit = {}, retryCount = 0, timeoutMs: number | undefined = 10000): Promise<any> {
  try {
    let effectiveToken: string | null = null;

    if (retryCount === 0) {
      effectiveToken = await ensureFreshToken();
    }

    if (!effectiveToken) {
      const token = getAuthToken();
      if (token && !isTokenExpired()) {
        effectiveToken = token;
      }
    }
    const headers = normalizeHeaders(options.headers as HeadersInit | undefined);

    ensureContentType(headers, options.body);

    if (effectiveToken && !findHeaderKey(headers, "Authorization")) {
      headers["Authorization"] = `Bearer ${effectiveToken}`;
    }

    const fullUrl = `${API_URL}${endpoint}`;
    const effectiveTimeoutMs = timeoutMs ?? 10000;

    // Only log non-GET requests to reduce noise from polling
    if (options.method && options.method !== 'GET') {
      console.log(`[API] Making ${options.method} request to: ${fullUrl}`);

      // Log request body for POST/PUT requests
      if (options.body) {
        console.log(`[API] Request body:`, options.body);
      }
    }

    const response = await fetch(fullUrl, {
      ...options,
      headers,
      // Add timeout to prevent hanging requests
      signal: AbortSignal.timeout(effectiveTimeoutMs),
    });

    if (!response.ok) {
      // Try to get error message from response body first
      let errorMessage = `Request failed with status ${response.status}`;
      try {
        const errorData = await response.json();
        if (Array.isArray(errorData?.detail)) {
          errorMessage = errorData.detail.map((d: any) => d?.msg || (d?.loc ? `${d.loc.join('.')}: ${d.type}` : JSON.stringify(d))).join('; ');
        } else if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        } else if (errorData?.message) {
          errorMessage = errorData.message;
        }
      } catch (parseError) {
        // If we can't parse the error response, use the default message
        console.warn('Could not parse error response:', parseError);
      }

      if (response.status === 401) {
        // Token expired or invalid - attempt auto re-login if this is the first retry
        if (retryCount === 0) {
          const refreshedToken = await ensureFreshToken();
          if (refreshedToken) {
            // Retry the original request with new token
            return fetchFromApi(endpoint, options, retryCount + 1);
          }
        }

        // Auto re-login failed or this is a retry - clear tokens and redirect to login
        clearAuthTokens();

        // Use the parsed error message if available, otherwise use default
        if (errorMessage === `Request failed with status ${response.status}`) {
          errorMessage = 'Authentication required';
        }

        // Redirect to login page only if not already there
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
      } else if (response.status === 403) {
        // Forbidden - attempt auto re-login if this is the first retry
        if (retryCount === 0) {
          const refreshedToken = await ensureFreshToken();
          if (refreshedToken) {
            // Retry the original request with new token
            return fetchFromApi(endpoint, options, retryCount + 1, timeoutMs);
          }
        }

        // Auto re-login failed or this is a retry - clear tokens and redirect to login
        clearAuthTokens();

        // Redirect to login page only if not already there
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }

        throw new Error('Authentication required');
      } else if (response.status === 404 && errorMessage === 'User not found') {
        // User not found - this indicates the user's token is invalid or user doesn't exist
        // Attempt auto re-login if this is the first retry
        if (retryCount === 0) {
          const refreshedToken = await ensureFreshToken();
          if (refreshedToken) {
            // Retry the original request with new token
            return fetchFromApi(endpoint, options, retryCount + 1, timeoutMs);
          }
        }

        // Auto re-login failed or this is a retry - clear tokens and redirect to login
        clearAuthTokens();

        // Redirect to login page only if not already there
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }

        throw new Error('Authentication required');
      }

      throw new Error(errorMessage);
    }

    // Handle responses with no content (204) or empty content
    if (response.status === 204 || !response.headers.get('content-length') || response.headers.get('content-length') === '0') {
      return null;
    }

    // For other successful responses, parse JSON
    const text = await response.text();
    if (!text) {
      // Only log non-GET requests to reduce noise from polling
      if (options.method && options.method !== 'GET') {
        console.log(`[API] ${options.method} ${fullUrl} - Empty response (${response.status})`);
      }
      return null;
    }

    const result = JSON.parse(text);
    // Only log non-GET requests to reduce noise from polling
    if (options.method && options.method !== 'GET') {
      console.log(`[API] ${options.method} ${fullUrl} - Success (${response.status}):`, result);
    }
    return result;
  } catch (error: any) {
    const isAbort = (error?.name === 'TimeoutError') || (error?.name === 'AbortError') || (error?.code === 'ERR_CANCELED');
    const method = (options.method || 'GET').toUpperCase();
    if (!(isAbort && method === 'GET')) {
      console.error('API request failed:', error);
    }
    throw error;
  }
}

// API endpoints
export const api = {
  // Generic HTTP methods
  get: async (url: string, config?: RequestInit & { timeout?: number }): Promise<any> => {
    const { timeout, ...requestConfig } = config ?? {};
    const effectiveTimeout = timeout ?? 10000;
    return fetchFromApi(url, { method: 'GET', ...requestConfig }, 0, effectiveTimeout);
  },

  post: async (url: string, data?: any, config?: RequestInit & { timeout?: number }): Promise<any> => {
    const { timeout, ...requestConfig } = config || {};
    return fetchFromApi(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...requestConfig,
    }, 0, timeout);
  },

  put: async (url: string, data?: any, config?: RequestInit): Promise<any> => {
    return fetchFromApi(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      ...config,
    });
  },

  delete: async (url: string, config?: RequestInit): Promise<any> => {
    return fetchFromApi(url, { method: 'DELETE', ...config });
  },

  // Health check
  getHealth: () => fetchFromApi('/api/v1/health'),


  // Authentication endpoints
  auth: {
    signUp: async (data: SignUpRequest): Promise<SignUpResponse> => {
      return fetchFromApi('/api/v1/auth/signup', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    confirmSignUp: async (data: ConfirmSignUpRequest): Promise<{ message: string }> => {
      return fetchFromApi('/api/v1/auth/confirm-signup', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    signIn: async (data: SignInRequest): Promise<SignInResponse> => {
      const response = await fetchFromApi('/api/v1/auth/signin', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      // Store tokens and user info
      storeAuthTokens(response);
      localStorage.setItem('user_info', JSON.stringify(response.user));

      return response;
    },

    silentSignInWithStoredCredentials: async (): Promise<boolean> => {
      const token = await ensureFreshToken();
      return Boolean(token);
    },

    getCurrentUser: async (): Promise<UserInfo> => {
      return fetchFromApi('/api/v1/auth/me');
    },
    updateCurrentUser: async (data: Partial<UserInfo>): Promise<UserInfo> => {
      return fetchFromApi('/api/v1/auth/me', {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    signOut: async (): Promise<{ message: string }> => {
      const response = await fetchFromApi('/api/v1/auth/signout', {
        method: 'POST',
      });

      // Clear stored tokens
      clearAuthTokens();

      return response;
    },

    changePassword: async (data: PasswordChangeRequest): Promise<PasswordChangeResponse> => {
      return fetchFromApi('/api/v1/auth/change-password', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    deleteAccount: async (data: DeleteAccountRequest): Promise<DeleteAccountResponse> => {
      const response = await fetchFromApi('/api/v1/auth/delete-account', {
        method: 'DELETE',
        body: JSON.stringify(data),
      });

      // Clear stored tokens and user info after successful deletion
      if (response.success) {
        clearAuthTokens();
      }

      return response;
    },

    // OAuth endpoints
    getGoogleOAuthUrl: async (): Promise<OAuthUrlResponse> => {
      return fetchFromApi('/api/v1/auth/oauth/google/url');
    },

    handleOAuthCallback: async (data: OAuthCallbackRequest): Promise<SignInResponse> => {
      const response = await fetchFromApi('/api/v1/auth/oauth/callback', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      // Store tokens and user info
      storeAuthTokens(response);
      localStorage.setItem('user_info', JSON.stringify(response.user));

      return response;
    },

    // Helper functions
    isAuthenticated: (): boolean => {
      const token = getAuthToken();
      return token !== null && !isTokenExpired();
    },

    getStoredUser: (): UserInfo | null => {
      const userInfo = localStorage.getItem('user_info');
      if (!userInfo) return null;

      try {
        return JSON.parse(userInfo);
      } catch (error) {
        // If JSON is invalid, clear it and return null
        localStorage.removeItem('user_info');
        return null;
      }
    },

    clearTokens: clearAuthTokens,
  },

  // LLM Integration endpoints
  llmIntegrations: {
    list: async (): Promise<LLMIntegrationResponse[]> => {
      return fetchFromApi('/api/v1/llm-integrations/');
    },

    get: async (integrationId: LLMIntegrationId): Promise<LLMIntegrationResponse> => {
      return fetchFromApi(`/api/v1/llm-integrations/${integrationId}`);
    },

    create: async (data: LLMIntegrationCreate): Promise<LLMIntegrationResponse> => {
      return fetchFromApi('/api/v1/llm-integrations/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    update: async (integrationId: LLMIntegrationId, data: LLMIntegrationUpdate): Promise<LLMIntegrationResponse> => {
      return fetchFromApi(`/api/v1/llm-integrations/${integrationId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    delete: async (integrationId: LLMIntegrationId): Promise<void> => {
      return fetchFromApi(`/api/v1/llm-integrations/${integrationId}`, {
        method: 'DELETE',
      });
    },

    setDefault: async (integrationId: LLMIntegrationId): Promise<LLMIntegrationResponse> => {
      return fetchFromApi(`/api/v1/llm-integrations/${integrationId}/set-default`, {
        method: 'POST',
      });
    },

    test: async (integrationId: LLMIntegrationId, testRequest: LLMTestRequest): Promise<LLMTestResponse> => {
      return fetchFromApi(`/api/v1/llm-integrations/${integrationId}/test`, {
        method: 'POST',
        body: JSON.stringify(testRequest),
      });
    },

    testApiKey: async (testRequest: {
      provider: string;
      api_key: string;
      model: string;
      test_prompt: string;
    }): Promise<LLMTestResponse> => {
      return fetchFromApi('/api/v1/llm-integrations/test-api-key', {
        method: 'POST',
        body: JSON.stringify(testRequest),
      });
    },

    getDefault: async (): Promise<LLMIntegrationResponse> => {
      return fetchFromApi('/api/v1/llm-integrations/default');
    },

    getAvailableModels: async (): Promise<ProviderModels> => {
      return fetchFromApi('/api/v1/llm-integrations/providers/models');
    },

    getAvailableModelsDetailed: async (): Promise<ProviderModelInfo[]> => {
      return fetchFromApi('/api/v1/llm-integrations/providers/models');
    },
  },

  // Tools endpoints
  tools: {
    list: async (params?: Record<string, any>): Promise<any[]> => {
      const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchFromApi(`/api/v1/tools${queryString}`);
    },

    get: async (id: ToolId): Promise<any> => {
      return fetchFromApi(`/api/v1/tools/${id}`);
    },

    create: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/tools', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    update: async (id: ToolId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/tools/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    clone: async (id: ToolId): Promise<any> => {
      return fetchFromApi(`/api/v1/tools/${id}/clone`, {
        method: 'POST',
      });
    },

    usage: async (id: ToolId): Promise<{ agents: { id: string; name: string }[]; agentsCount: number }> => {
      return fetchFromApi(`/api/v1/tools/${id}/usage`);
    },

    delete: async (id: ToolId, options?: { detach_from_agents?: boolean }): Promise<void> => {
      const qp = options?.detach_from_agents ? '?detach_from_agents=true' : '';
      return fetchFromApi(`/api/v1/tools/${id}${qp}`, {
        method: 'DELETE',
      });
    },
  },

  // Billing endpoints
  billing: {
    listBundles: async (): Promise<{ bundles: Array<{ id: string; name: string; coins: number; currency: string; amount_cents: number; price_id?: string; payment_link_url?: string }> }> => {
      return fetchFromApi('/api/v1/billing/bundles');
    },
    createCheckoutSession: async (bundleId: string): Promise<{ checkout_url: string; session_id: string }> => {
      return fetchFromApi('/api/v1/billing/checkout-session', {
        method: 'POST',
        body: JSON.stringify({ bundle_id: bundleId })
      });
    },
    confirmSession: async (sessionId: string): Promise<{ status: 'credited' | 'pending' | 'invalid'; coins_added: number }> => {
      return fetchFromApi('/api/v1/billing/confirm-session', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId })
      });
    },
  },

  errorReports: {
    create: async (data: ErrorReportCreateRequest): Promise<ErrorReportResponse> => {
      const fallbackUrl = typeof window !== 'undefined' ? window.location.href : null;
      const fallbackUserAgent = typeof navigator !== 'undefined' ? navigator.userAgent : null;

      const payload = {
        message: data.message,
        name: data.name ?? null,
        stack: data.stack ?? null,
        component_stack: data.componentStack ?? null,
        url: data.url ?? fallbackUrl,
        user_agent: data.userAgent ?? fallbackUserAgent,
  metadata: data.metadata ?? null,
      } satisfies Record<string, unknown>;

      return fetchFromApi('/api/v1/error-reports', {
        method: 'POST',
        body: JSON.stringify(payload),
      }) as Promise<ErrorReportResponse>;
    },
  },

  // Avatar endpoints
  avatars: {
    // User avatar endpoints
    uploadUserAvatar: async (
      file: File,
      cropData?: { x: number; y: number; size: number; scale: number },
      theme?: 'light' | 'dark'
    ): Promise<{ message: string; avatarUrl: string }> => {
      const formData = new FormData();
      formData.append('file', file);

      // Build URL with crop parameters if provided
      const params = new URLSearchParams();
      if (cropData) {
        params.append('crop_x', cropData.x.toString());
        params.append('crop_y', cropData.y.toString());
        params.append('crop_size', cropData.size.toString());
        params.append('crop_scale', cropData.scale.toString());
      }
      if (theme) {
        params.append('theme', theme);
      }

      const url = `/api/v1/users/me/avatar${params.toString() ? `?${params.toString()}` : ''}`;

      return fetchFromApi(url, {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    },

    resetUserAvatar: async (): Promise<{ message: string; avatarUrl: string }> => {
      const res = await fetchFromApi('/api/v1/users/me/avatar', {
        method: 'DELETE',
      });
      return { message: res?.message ?? '', avatarUrl: res?.avatar_url ?? '' };
    },

    getUserAvatar: async (): Promise<{ avatarUrl: string; avatarType: string }> => {
      const res = await fetchFromApi('/api/v1/users/me/avatar');
      return { avatarUrl: res?.avatar_url ?? '', avatarType: res?.avatar_type ?? '' };
    },

    // Agent avatar endpoints
    uploadAgentAvatar: async (
      agentId: string,
      file: File,
      cropData?: { x: number; y: number; size: number; scale: number },
      theme?: 'light' | 'dark'
    ): Promise<{ message: string; avatarUrl: string }> => {
      const formData = new FormData();
      formData.append('file', file);

      // Build URL with crop parameters if provided
      const params = new URLSearchParams();
      if (cropData) {
        params.append('crop_x', cropData.x.toString());
        params.append('crop_y', cropData.y.toString());
        params.append('crop_size', cropData.size.toString());
        params.append('crop_scale', cropData.scale.toString());
      }
      if (theme) {
        params.append('theme', theme);
      }

      const url = `/api/v1/agents/${agentId}/avatar${params.toString() ? `?${params.toString()}` : ''}`;

      return fetchFromApi(url, {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    },

    resetAgentAvatar: async (agentId: string): Promise<{ message: string; avatarUrl: string }> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/avatar`, {
        method: 'DELETE',
      });
    },

    getAgentAvatar: async (agentId: string): Promise<{ avatarUrl: string; avatarType: string }> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/avatar`);
    },
  },

  // Agents endpoints
  agents: {
    list: async (params?: Record<string, any>): Promise<any[]> => {
      const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchFromApi(`/api/v1/agents${queryString}`);
    },

    get: async (id: AgentId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${id}`);
    },

    create: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/agents', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    update: async (id: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    delete: async (id: AgentId): Promise<void> => {
      return fetchFromApi(`/api/v1/agents/${id}`, {
        method: 'DELETE',
      });
    },

    clone: async (id: AgentId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${id}/clone`, {
        method: 'POST',
      });
    },

    // Agent Version endpoints
    getVersions: async (agentId: AgentId): Promise<any[]> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions`);
    },

    getVersion: async (agentId: AgentId, versionId: AgentVersionId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/${versionId}`);
    },

    getActiveVersion: async (agentId: AgentId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/active`);
    },

    activateVersion: async (agentId: AgentId, versionId: AgentVersionId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/${versionId}/activate`, {
        method: 'POST',
      });
    },

    createVersion: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    updateVersion: async (agentId: AgentId, versionId: AgentVersionId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/${versionId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    rollbackVersion: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/rollback`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    compareVersions: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/compare`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    getVersionLimitInfo: async (agentId: AgentId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/versions/limit`);
    },

    // Agent Statistics endpoints
    getStatistics: async (agentId: AgentId): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/statistics`);
    },

    updateStatistics: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/statistics`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    // Agent Execution endpoints
    executeDecision: async (agentId: AgentId, data: any): Promise<any> => {
      // Support optional query params expected by backend function signature
      const {
        execution_session_id,
        test_scenario_id,
        game_id,
        move_number,
        game_state,
        ...rest
      } = data || {};
      const params: Record<string, any> = {};
      if (execution_session_id != null) params.execution_session_id = execution_session_id;
      if (test_scenario_id != null) params.test_scenario_id = test_scenario_id;
      if (game_id != null) params.game_id = game_id;
      if (move_number != null) params.move_number = move_number;
      const queryString = Object.keys(params).length ? `?${new URLSearchParams(params as any).toString()}` : '';
      return fetchFromApi(`/api/v1/agents/${agentId}/execute${queryString}`,
        {
          method: 'POST',
          body: JSON.stringify({ game_state: game_state ?? (rest?.game_state ?? {}) }),
        }
      );
    },

    validateResponse: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/validate-response`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
    // New test mechanism endpoints
    generateTestJson: async (agentId: string): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/generate-test-json`, {
        method: 'POST',
      });
    },
    testAgent: async (agentId: string, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/test`, {
        method: 'POST',
        body: JSON.stringify(data),
      }, 0, 300000); // 5 minute timeout for agent testing
    },
    generateState: async (agentId: AgentId, data: { description: string; llmIntegrationId: string }): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/generate-state`, {
        method: 'POST',
        body: JSON.stringify({ description: data.description, llm_integration_id: data.llmIntegrationId }),
      }, 0, 60000); // 1 minute timeout for state generation
    },

    // Test Scenario endpoints
    getTestScenarios: async (params?: Record<string, any>): Promise<any[]> => {
      const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchFromApi(`/api/v1/agents/test-scenarios${queryString}`);
    },

    getTestScenario: async (id: string): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/test-scenarios/${id}`);
    },

    createTestScenario: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/agents/test-scenarios', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    updateTestScenario: async (id: string, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/test-scenarios/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    deleteTestScenario: async (id: string): Promise<void> => {
      return fetchFromApi(`/api/v1/agents/test-scenarios/${id}`, {
        method: 'DELETE',
      });
    },

    // Environment info endpoints
    listEnvironments: async (): Promise<Array<{ id: string; metadata: any }>> => {
      return fetchFromApi(`/api/v1/agents/environments`);
    },

    // Environment Schema endpoints
    getEnvironmentSchema: async (environment: string): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/environments/${environment}/schema`);
    },

    getAutocomplete: async (environment: string, params: Record<string, any>): Promise<any> => {
      const queryString = new URLSearchParams(params).toString();
      return fetchFromApi(`/api/v1/agents/environments/${environment}/autocomplete?${queryString}`);
    },

    validatePrompt: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/agents/validate-prompt', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    // Synthetic Data Generation endpoints
    generateTestData: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/agents/generate-test-data', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    saveTestScenario: async (data: any): Promise<any> => {
      return fetchFromApi('/api/v1/agents/save-test-scenario', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    // Game State Management endpoints
    saveGameState: async (agentId: AgentId, data: any): Promise<any> => {
      return fetchFromApi(`/api/v1/agents/${agentId}/save-game-state`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    getSavedGameStates: async (agentId: AgentId, params?: { tags?: string[]; skip?: number; limit?: number }): Promise<any[]> => {
      const searchParams = new URLSearchParams();
      if (params?.tags) {
        params.tags.forEach(tag => searchParams.append('tags', tag));
      }
      if (params?.skip !== undefined) {
        searchParams.append('skip', params.skip.toString());
      }
      if (params?.limit !== undefined) {
        searchParams.append('limit', params.limit.toString());
      }

      const queryString = searchParams.toString();
      const url = `/api/v1/agents/${agentId}/saved-game-states${queryString ? `?${queryString}` : ''}`;

      return fetchFromApi(url);
    },
  },
};

export default api;
