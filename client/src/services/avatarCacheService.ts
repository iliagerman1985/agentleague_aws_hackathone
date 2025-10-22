/**
 * Avatar Cache Service
 * 
 * Provides two-tier caching for avatar data:
 * 1. In-memory cache for fast access during the session
 * 2. localStorage persistence for cross-session caching
 * 
 * Only caches data URLs (base64 encoded avatars), not external URLs.
 */

// In-memory cache for avatar data
const avatarCache = new Map<string, { avatarUrl: string | null; avatarType: string }>();

// LocalStorage key prefix
const STORAGE_PREFIX = 'avatar_cache_';
const CACHE_VERSION = 'v1';
const CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

interface CachedAvatar {
  avatarUrl: string | null;
  avatarType: string;
  timestamp: number;
  version: string;
}

/**
 * Check if a cached avatar is still valid
 */
function isValidCache(cached: CachedAvatar): boolean {
  if (cached.version !== CACHE_VERSION) return false;
  const age = Date.now() - cached.timestamp;
  return age < CACHE_EXPIRY_MS;
}

/**
 * Load avatar from localStorage
 */
function loadFromStorage(key: string): { avatarUrl: string | null; avatarType: string } | null {
  try {
    const stored = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
    if (!stored) return null;

    const cached: CachedAvatar = JSON.parse(stored);
    if (!isValidCache(cached)) {
      localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
      return null;
    }

    return {
      avatarUrl: cached.avatarUrl,
      avatarType: cached.avatarType,
    };
  } catch (error) {
    console.warn('Failed to load avatar from localStorage:', error);
    return null;
  }
}

/**
 * Save avatar to localStorage
 * Caches both data URLs and file paths as-is
 */
function saveToStorage(key: string, avatar: { avatarUrl: string | null; avatarType: string }): void {
  if (!avatar.avatarUrl) {
    return;
  }

  try {
    const cached: CachedAvatar = {
      avatarUrl: avatar.avatarUrl,
      avatarType: avatar.avatarType,
      timestamp: Date.now(),
      version: CACHE_VERSION,
    };
    localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(cached));
  } catch (error) {
    console.warn('Failed to save avatar to localStorage:', error);
  }
}

export const avatarCacheService = {
  /**
   * Get avatar from cache (memory or localStorage)
   */
  get(key: string): { avatarUrl: string | null; avatarType: string } | null {
    // Check memory cache first
    if (avatarCache.has(key)) {
      return avatarCache.get(key)!;
    }

    // Check localStorage
    const stored = loadFromStorage(key);
    if (stored) {
      // Populate memory cache
      avatarCache.set(key, stored);
      return stored;
    }

    return null;
  },

  /**
   * Set avatar in cache (both memory and localStorage)
   */
  set(key: string, avatar: { avatarUrl: string | null; avatarType: string }): void {
    avatarCache.set(key, avatar);
    saveToStorage(key, avatar);
  },

  /**
   * Check if avatar exists in cache
   */
  has(key: string): boolean {
    return avatarCache.has(key) || loadFromStorage(key) !== null;
  },

  /**
   * Preload multiple avatars at once
   * Returns a map of successfully loaded avatars
   */
  async preloadAvatars(
    keys: string[],
    fetchFn: (key: string) => Promise<{ avatarUrl: string | null; avatarType: string } | null>
  ): Promise<Map<string, { avatarUrl: string | null; avatarType: string }>> {
    const results = new Map<string, { avatarUrl: string | null; avatarType: string }>();

    // Separate cached and uncached keys
    const uncachedKeys: string[] = [];
    for (const key of keys) {
      const cached = this.get(key);
      if (cached) {
        results.set(key, cached);
      } else {
        uncachedKeys.push(key);
      }
    }

    // Fetch uncached avatars in parallel
    if (uncachedKeys.length > 0) {
      const fetchPromises = uncachedKeys.map(async (key) => {
        try {
          const avatar = await fetchFn(key);
          if (avatar) {
            this.set(key, avatar);
            results.set(key, avatar);
          }
        } catch (error) {
          console.warn(`Failed to fetch avatar for key ${key}:`, error);
        }
      });

      await Promise.all(fetchPromises);
    }

    return results;
  },

  /**
   * Clear all cached avatars
   */
  clearAll(): void {
    avatarCache.clear();

    // Clear from localStorage
    try {
      const keys = Object.keys(localStorage);
      keys.forEach((key) => {
        if (key.startsWith(STORAGE_PREFIX)) {
          localStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.warn('Failed to clear avatar cache from localStorage:', error);
    }
  },

  /**
   * Clear specific avatar
   */
  clear(key: string): void {
    avatarCache.delete(key);
    try {
      localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
    } catch (error) {
      console.warn('Failed to clear avatar from localStorage:', error);
    }
  },

  /**
   * Get cache statistics
   */
  getStats(): { memorySize: number; storageSize: number } {
    let storageSize = 0;
    try {
      const keys = Object.keys(localStorage);
      keys.forEach((key) => {
        if (key.startsWith(STORAGE_PREFIX)) {
          storageSize++;
        }
      });
    } catch (error) {
      console.warn('Failed to get storage stats:', error);
    }

    return {
      memorySize: avatarCache.size,
      storageSize,
    };
  },
};

