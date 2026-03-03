# Enhanced backend improvements for update_ai_insights.py

import redis
import time
from functools import wraps
from typing import Optional, Dict, Any

def rate_limit(calls_per_minute: int = 60):
    """Decorator to enforce API rate limiting"""
    def decorator(func):
        func._call_times = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls older than 1 minute
            func._call_times = [t for t in func._call_times if now - t < 60]
            
            if len(func._call_times) >= calls_per_minute:
                wait_time = 60 - (now - func._call_times[0])
                print(f"Rate limit hit for {func.__name__}, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            func._call_times.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

class CacheManager:
    """Simple caching for API responses"""
    def __init__(self):
        self.cache = {}
        self.cache_ttl = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            if time.time() < self.cache_ttl.get(key, 0):
                return self.cache[key]
            else:
                # Cache expired
                del self.cache[key]
                if key in self.cache_ttl:
                    del self.cache_ttl[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        self.cache[key] = value
        self.cache_ttl[key] = time.time() + ttl_seconds

# Global cache instance
cache = CacheManager()

@rate_limit(calls_per_minute=12)  # Alpha Vantage rate limit
def get_alpha_vantage_data_cached(symbol: str) -> Dict[str, Any]:
    """Cached Alpha Vantage API calls"""
    cache_key = f"alpha_{symbol}"
    cached = cache.get(cache_key)
    if cached:
        print(f"Using cached Alpha Vantage data for {symbol}")
        return cached
    
    # Original API call here
    result = get_alpha_vantage_analysis(symbol)  # Your existing function
    cache.set(cache_key, result, ttl_seconds=300)  # 5 minute cache
    return result

@rate_limit(calls_per_minute=100)  # Polygon rate limit
def get_polygon_data_cached(endpoint: str) -> Dict[str, Any]:
    """Cached Polygon API calls"""
    cache_key = f"polygon_{endpoint}"
    cached = cache.get(cache_key)
    if cached:
        print(f"Using cached Polygon data for {endpoint}")
        return cached
    
    # Original API call here  
    result = get_polygon_sentiment()  # Your existing function
    cache.set(cache_key, result, ttl_seconds=180)  # 3 minute cache
    return result

def validate_api_response(data: Dict[str, Any], required_fields: list) -> bool:
    """Validate API response has required fields"""
    if not isinstance(data, dict):
        return False
    return all(field in data for field in required_fields)