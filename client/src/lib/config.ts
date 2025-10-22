/**
 * Configuration service for the application
 * Loads configuration from environment variables with fallbacks
 */

interface AppConfig {
  apiUrl: string;
  // Add other configuration properties as needed
}

/**
 * Get the API URL from environment variables or use a fallback
 * In development, this will use the value from .env.development
 * In production, this will use the value from .env.production
 */
function getApiUrl(): string {
  // Use environment variable if available (injected by Vite)
  // Note: Check for undefined, not falsy, to allow empty string
  if (import.meta.env.VITE_API_URL !== undefined) {
    const apiUrl = import.meta.env.VITE_API_URL;
    // If empty string and we're in dev mode, use localhost fallback
    if (apiUrl === '' && import.meta.env.DEV) {
      return 'http://localhost:9998';
    }
    return apiUrl;
  }

  // Fallback based on current environment
  if (import.meta.env.DEV) {
    return 'http://localhost:9998';
  }

  // Production fallback (could be a relative URL if API is served from same domain)
  return '/api';
}

/**
 * Application configuration
 */
const config: AppConfig = {
  apiUrl: getApiUrl(),
};

// Log configuration for debugging
console.log('[CONFIG] Environment variables:');
console.log('[CONFIG] VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('[CONFIG] DEV mode:', import.meta.env.DEV);
console.log('[CONFIG] Final API URL:', config.apiUrl);

export default config;
