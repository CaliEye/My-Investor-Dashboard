// Enhanced data management with caching and error resilience
class DataManager {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute cache
    this.retryAttempts = 3;
    this.retryDelay = 1000;
  }

  async fetchWithCache(url, options = {}) {
    const cacheKey = url;
    const cached = this.cache.get(cacheKey);
    
    if (cached && (Date.now() - cached.timestamp < this.cacheTimeout)) {
      console.log(`[Cache] Using cached data for ${url}`);
      return cached.data;
    }

    try {
      const data = await this.fetchWithRetry(url, options);
      this.cache.set(cacheKey, {
        data,
        timestamp: Date.now()
      });
      return data;
    } catch (error) {
      console.error(`[DataManager] Failed to fetch ${url}:`, error);
      // Return cached data if available, even if expired
      if (cached) {
        console.warn(`[DataManager] Using expired cache for ${url}`);
        return cached.data;
      }
      throw error;
    }
  }

  async fetchWithRetry(url, options = {}, attempt = 1) {
    try {
      const response = await fetch(url, {
        ...options,
        cache: 'no-store',
        signal: AbortSignal.timeout(10000) // 10 second timeout
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      if (attempt < this.retryAttempts) {
        console.warn(`[DataManager] Retry ${attempt}/${this.retryAttempts} for ${url}`);
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
        return this.fetchWithRetry(url, options, attempt + 1);
      }
      throw error;
    }
  }

  clearCache() {
    this.cache.clear();
    console.log('[DataManager] Cache cleared');
  }

  getCacheStats() {
    return {
      size: this.cache.size,
      entries: Array.from(this.cache.keys())
    };
  }
}

// Global data manager instance
window.dataManager = new DataManager();