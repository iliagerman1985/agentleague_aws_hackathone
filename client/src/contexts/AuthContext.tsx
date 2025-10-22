import React, { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react';
import { api, UserInfo } from '@/lib/api';

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  handleAuthError: () => Promise<void>;
  updateCoinsBalance: (newBalance: number) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const initRef = useRef(false);

  const isAuthenticated = user !== null && api.auth.isAuthenticated();

  // Initialize auth state on mount - simplified to avoid blocking
  useEffect(() => {
    // Prevent double initialization in React StrictMode
    if (initRef.current) {
      console.log('AuthContext: Skipping duplicate initialization');
      return;
    }
    initRef.current = true;

    const initializeAuth = async () => {
      console.log('AuthContext: Starting initialization...');
      try {
        if (api.auth.isAuthenticated()) {
          console.log('AuthContext: Found existing auth tokens');
          const storedUser = api.auth.getStoredUser();
          if (storedUser) {
            console.log('AuthContext: Using stored user');
            setUser(storedUser);
          } else {
            const fullUser = await api.auth.getCurrentUser();
            setUser(fullUser);
            localStorage.setItem('user_info', JSON.stringify(fullUser));
          }
        } else {
          console.log('AuthContext: No auth tokens found, attempting silent re-authentication');
          const silentSuccess = await api.auth.silentSignInWithStoredCredentials();
          if (silentSuccess && api.auth.isAuthenticated()) {
            const refreshedUser = api.auth.getStoredUser();
            if (refreshedUser) {
              setUser(refreshedUser);
            } else {
              const currentUser = await api.auth.getCurrentUser();
              setUser(currentUser);
              localStorage.setItem('user_info', JSON.stringify(currentUser));
            }
          } else {
            console.log('AuthContext: Silent re-authentication unavailable, clearing state');
            api.auth.clearTokens();
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        api.auth.clearTokens();
        setUser(null);
      } finally {
        console.log('AuthContext: Initialization complete, setting isLoading to false');
        setIsLoading(false);
      }
    };

    void initializeAuth();
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await api.auth.signIn({ email, password });
      console.log('AuthContext: Sign-in successful, initial user:', response.user);
      // Immediately refresh to get full profile including avatar
      const fullUser = await api.auth.getCurrentUser();
      setUser(fullUser);
      localStorage.setItem('user_info', JSON.stringify(fullUser));
      console.log('AuthContext: Full user profile loaded:', fullUser);
      // Small delay to ensure tokens are stored and state is updated
      await new Promise(resolve => setTimeout(resolve, 100));
    } catch (error) {
      console.error('Sign in error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signOut = async () => {
    try {
      setIsLoading(true);
      await api.auth.signOut();
    } catch (error) {
      console.error('Sign out error:', error);
      // Even if server request fails, clear local state
    } finally {
      // Store current location before clearing auth state
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/register') {
        localStorage.setItem('preLogoutLocation', currentPath);
      }

      api.auth.clearTokens();
      setUser(null);
      setIsLoading(false);
      // Small delay to ensure state updates are processed
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  };

  const refreshUser = async () => {
    try {
      if (api.auth.isAuthenticated()) {
        const currentUser = await api.auth.getCurrentUser();
        setUser(currentUser);
        localStorage.setItem('user_info', JSON.stringify(currentUser));
      }
    } catch (error) {
      console.error('Refresh user error:', error);
      // If refresh fails, sign out
      await signOut();
    }
  };

  const handleAuthError = async () => {
    try {
      const silentSuccess = await api.auth.silentSignInWithStoredCredentials();
      if (silentSuccess) {
        console.log('Automatic re-login successful');
        await refreshUser();
        return;
      }
    } catch (error) {
      console.warn('Automatic re-login failed:', error);
      // Clear stored credentials to prevent infinite loop
      localStorage.removeItem('rememberedEmail');
      localStorage.removeItem('rememberedPassword');
    }

    // Store current location before signing out due to auth error
    const currentPath = window.location.pathname;
    if (currentPath !== '/login' && currentPath !== '/register') {
      localStorage.setItem('preLogoutLocation', currentPath);
    }

    // If auto re-login fails or no stored credentials, sign out
    await signOut();
  };

  const updateCoinsBalance = (newBalance: number) => {
    if (user) {
      const updatedUser = { ...user, coinsBalance: newBalance };
      setUser(updatedUser);
      localStorage.setItem('user_info', JSON.stringify(updatedUser));
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    signIn,
    signOut,
    refreshUser,
    handleAuthError,
    updateCoinsBalance,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
