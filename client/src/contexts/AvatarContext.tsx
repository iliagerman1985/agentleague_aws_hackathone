import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useAppearance } from './AppearanceContext';

interface AvatarState {
  avatarUrl: string | null;
  avatarType: 'default' | 'google' | 'uploaded';
}

interface AvatarContextType {
  // User avatar state
  userAvatar: AvatarState;
  setUserAvatar: (avatar: AvatarState) => void;
  refreshUserAvatar: () => Promise<void>;

  // Agent avatar state (for agent editing)
  agentAvatar: AvatarState;
  setAgentAvatar: (avatar: AvatarState) => void;

  // Loading state
  isLoading: boolean;

  // Utility functions
  uploadAvatar: (
    file: File,
    type?: 'user' | 'agent',
    cropData?: { x: number; y: number; size: number; scale: number }
  ) => Promise<string>;
  removeAvatar: (type?: 'user' | 'agent') => Promise<void>;
}

const AvatarContext = createContext<AvatarContextType | undefined>(undefined);

export const useAvatar = () => {
  const context = useContext(AvatarContext);
  if (context === undefined) {
    throw new Error('useAvatar must be used within an AvatarProvider');
  }
  return context;
};

interface AvatarProviderProps {
  children: ReactNode;
}

export const AvatarProvider: React.FC<AvatarProviderProps> = ({ children }) => {
  const { user, refreshUser } = useAuth();
  const { actualTheme } = useAppearance();

  // User avatar state
  const [userAvatar, setUserAvatarState] = useState<AvatarState>({
    avatarUrl: null,
    avatarType: 'default'
  });

  // Agent avatar state (for agent editing)
  const [agentAvatar, setAgentAvatarState] = useState<AvatarState>({
    avatarUrl: null,
    avatarType: 'default'
  });

  const [isLoading, setIsLoading] = useState(false);

  // Initialize user avatar from auth context - simplified approach
  useEffect(() => {
    if (user) {
      const avatarType = (user.avatarType ?? 'default') as 'default' | 'google' | 'uploaded';
      let avatarUrl = avatarType === 'default' ? null : (user.avatarUrl ?? null);
      // One-time cache bust for uploaded avatars on first load; skip for data URLs
      const isData = typeof avatarUrl === 'string' && avatarUrl.startsWith('data:');
      if (avatarType === 'uploaded' && avatarUrl && !isData && !/[?&]t=/.test(avatarUrl)) {
        avatarUrl = `${avatarUrl}${avatarUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
      }

      // Only update if the current state is different from user data
      // This prevents overriding manual state updates during upload
      setUserAvatarState(current => {
        const shouldUpdate = current.avatarUrl !== avatarUrl || current.avatarType !== avatarType;
        return shouldUpdate ? { avatarUrl: avatarUrl, avatarType: avatarType } : current;
      });
    } else {
      // Reset to default when user is null
      setUserAvatarState({ avatarUrl: null, avatarType: 'default' });
    }
  }, [user?.avatarUrl, user?.avatarType]);

  // User avatar setters
  const setUserAvatar = (avatar: AvatarState) => {
    setUserAvatarState(avatar);
  };

  const setAgentAvatar = (avatar: AvatarState) => {
    setAgentAvatarState(avatar);
  };

  // Refresh user avatar from server
  const refreshUserAvatar = async () => {
    try {
      setIsLoading(true);
      await refreshUser(); // This will update the user in AuthContext
      // The effect above will automatically sync the avatar state
    } catch (error) {
      console.error('Failed to refresh user avatar:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // On first mount, refresh user once if authenticated to ensure avatar info is present
  useEffect(() => {
    if (api.auth.isAuthenticated()) {
      // Fire and forget; Avatar state will sync via the effect above
      refreshUser().catch(err => console.warn('AvatarProvider: refresh on mount failed', err));
    }
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Upload avatar function
  const uploadAvatar = async (
    file: File,
    type: 'user' | 'agent' = 'user',
    cropData?: { x: number; y: number; size: number; scale: number }
  ): Promise<string> => {
    try {
      setIsLoading(true);

      if (type === 'user') {
        const response = await api.avatars.uploadUserAvatar(file, cropData, actualTheme);
        // Add cache-busting timestamp only for non-data URLs
        const u = response.avatarUrl;
        const isData = typeof u === 'string' && u.startsWith('data:');
        const avatarUrlWithTimestamp = isData ? u : `${u}${u.includes('?') ? '&' : '?'}t=${Date.now()}`;
        // Update state immediately for better UX
        setUserAvatarState({
          avatarUrl: avatarUrlWithTimestamp,
          avatarType: 'uploaded'
        });
        // Refresh user data to sync with backend
        await refreshUser();
        return response.avatarUrl;
      } else {
        const response = await api.avatars.uploadAgentAvatar('temp', file, cropData, actualTheme);
        // Add cache-busting timestamp only for non-data URLs
        const u = response.avatarUrl;
        const isData = typeof u === 'string' && u.startsWith('data:');
        const avatarUrlWithTimestamp = isData ? u : `${u}${u.includes('?') ? '&' : '?'}t=${Date.now()}`;
        setAgentAvatarState({
          avatarUrl: avatarUrlWithTimestamp,
          avatarType: 'uploaded'
        });
        return response.avatarUrl;
      }
    } catch (error) {
      console.error(`Failed to upload ${type} avatar:`, error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Remove avatar function
  const removeAvatar = async (type: 'user' | 'agent' = 'user') => {
    try {
      setIsLoading(true);

      if (type === 'user') {
        await api.avatars.resetUserAvatar();
        // Update state immediately for better UX
        setUserAvatarState({
          avatarUrl: null,
          avatarType: 'default'
        });
      } else {
        await api.avatars.resetAgentAvatar('temp');
        setAgentAvatarState({
          avatarUrl: null,
          avatarType: 'default'
        });
      }
    } catch (error) {
      console.error(`Failed to remove ${type} avatar:`, error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const value: AvatarContextType = {
    userAvatar,
    setUserAvatar,
    refreshUserAvatar,
    agentAvatar,
    setAgentAvatar,
    isLoading,
    uploadAvatar,
    removeAvatar,
  };

  return (
    <AvatarContext.Provider value={value}>
      {children}
    </AvatarContext.Provider>
  );
};