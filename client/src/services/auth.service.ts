import { SignInRequest, SignInResponse, UserInfo } from '../lib/api';
import { StorageService } from './storage';

/**
 * Authentication service implementation
 */
export class AuthService {
  constructor(private storage: StorageService) {}

  getAuthToken(): string | null {
    const token = this.storage.get('access_token');
    if (!token) return null;

    // Check if token is expired
    const expiresAt = this.storage.get('expires_at');
    if (expiresAt && Date.now() >= parseInt(expiresAt, 10)) {
      this.clearTokens();
      return null;
    }

    return token;
  }

  storeTokens(response: SignInResponse): void {
    this.storage.set('access_token', response.accessToken);
    if (response.idToken) {
      this.storage.set('id_token', response.idToken);
    }
    
    // Calculate expiration time
    const expiresAt = Date.now() + (response.expiresIn * 1000);
    this.storage.set('expires_at', expiresAt.toString());
    
    // Store user info if provided
    if (response.user) {
      this.storage.set('user_info', JSON.stringify(response.user));
    }
  }

  clearTokens(): void {
    this.storage.remove('access_token');
    this.storage.remove('id_token');
    this.storage.remove('expires_at');
    this.storage.remove('user_info');
  }

  isAuthenticated(): boolean {
    const token = this.getAuthToken();
    return token !== null;
  }

  getStoredUser(): UserInfo | null {
    const userInfo = this.storage.get('user_info');
    if (!userInfo) return null;
    
    try {
      return JSON.parse(userInfo);
    } catch (error) {
      console.warn('Failed to parse stored user info:', error);
      // Clear invalid data
      this.storage.remove('user_info');
      return null;
    }
  }

  // These methods would typically make HTTP requests
  // For now, they're placeholders that would be implemented with actual API calls
  async signIn(_data: SignInRequest): Promise<SignInResponse> {
    throw new Error('Method not implemented - should be handled by API layer');
  }

  async signOut(): Promise<{ message: string }> {
    throw new Error('Method not implemented - should be handled by API layer');
  }

  async getCurrentUser(): Promise<UserInfo> {
    throw new Error('Method not implemented - should be handled by API layer');
  }
}
