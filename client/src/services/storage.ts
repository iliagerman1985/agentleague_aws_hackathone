/**
 * Storage service interfaces and implementations
 */

// Storage interface that both localStorage and mock storage will implement
export interface IStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  clear(): void;
  key(index: number): string | null;
  readonly length: number;
}

// Storage service that wraps the storage implementation
export class StorageService {
  constructor(private storage: IStorage) {}

  // Basic storage operations
  get(key: string): string | null {
    try {
      return this.storage.getItem(key);
    } catch (error) {
      console.warn(`Failed to get item from storage: ${key}`, error);
      return null;
    }
  }

  set(key: string, value: string): void {
    try {
      this.storage.setItem(key, value);
    } catch (error) {
      console.warn(`Failed to set item in storage: ${key}`, error);
    }
  }

  remove(key: string): void {
    try {
      this.storage.removeItem(key);
    } catch (error) {
      console.warn(`Failed to remove item from storage: ${key}`, error);
    }
  }

  clear(): void {
    try {
      this.storage.clear();
    } catch (error) {
      console.warn('Failed to clear storage', error);
    }
  }

  // JSON helpers
  getJson<T>(key: string): T | null {
    const value = this.get(key);
    if (!value) return null;

    try {
      return JSON.parse(value) as T;
    } catch (error) {
      console.warn(`Failed to parse JSON from storage: ${key}`, error);
      // Clear invalid data
      this.remove(key);
      return null;
    }
  }

  setJson<T>(key: string, value: T): void {
    try {
      const jsonString = JSON.stringify(value);
      this.set(key, jsonString);
    } catch (error) {
      console.warn(`Failed to stringify JSON for storage: ${key}`, error);
    }
  }

  // Utility methods
  has(key: string): boolean {
    return this.get(key) !== null;
  }

  keys(): string[] {
    const keys: string[] = [];
    try {
      for (let i = 0; i < this.storage.length; i++) {
        const key = this.storage.key(i);
        if (key) keys.push(key);
      }
    } catch (error) {
      console.warn('Failed to get storage keys', error);
    }
    return keys;
  }

  // Token-specific helpers
  getToken(key: string): string | null {
    return this.get(key);
  }

  setToken(key: string, token: string): void {
    this.set(key, token);
  }

  removeToken(key: string): void {
    this.remove(key);
  }

  // Expiry helpers
  setWithExpiry(key: string, value: string, expiryMs: number): void {
    const expiryTime = Date.now() + expiryMs;
    this.set(key, value);
    this.set(`${key}_expiry`, expiryTime.toString());
  }

  getWithExpiry(key: string): string | null {
    const value = this.get(key);
    const expiryStr = this.get(`${key}_expiry`);

    if (!value || !expiryStr) {
      return value;
    }

    const expiry = parseInt(expiryStr, 10);
    if (Date.now() > expiry) {
      // Expired, remove both value and expiry
      this.remove(key);
      this.remove(`${key}_expiry`);
      return null;
    }

    return value;
  }

  isExpired(key: string): boolean {
    const expiryStr = this.get(`${key}_expiry`);
    if (!expiryStr) return false;

    const expiry = parseInt(expiryStr, 10);
    return Date.now() > expiry;
  }
}

// Real localStorage implementation wrapper
export class BrowserStorageAdapter implements IStorage {
  constructor(private browserStorage: Storage = localStorage) {}

  getItem(key: string): string | null {
    return this.browserStorage.getItem(key);
  }

  setItem(key: string, value: string): void {
    this.browserStorage.setItem(key, value);
  }

  removeItem(key: string): void {
    this.browserStorage.removeItem(key);
  }

  clear(): void {
    this.browserStorage.clear();
  }

  key(index: number): string | null {
    return this.browserStorage.key(index);
  }

  get length(): number {
    return this.browserStorage.length;
  }
}

// Mock storage implementation for testing
export class MockStorageAdapter implements IStorage {
  private store: Map<string, string> = new Map();

  getItem(key: string): string | null {
    return this.store.get(key) || null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  key(index: number): string | null {
    const keys = Array.from(this.store.keys());
    return keys[index] || null;
  }

  get length(): number {
    return this.store.size;
  }

  // Testing helpers
  getStore(): Map<string, string> {
    return new Map(this.store);
  }

  setStore(data: Record<string, string>): void {
    this.store.clear();
    Object.entries(data).forEach(([key, value]) => {
      this.store.set(key, value);
    });
  }
}
