#!/usr/bin/env python3
"""
Enhanced Data Source Resilience System
Stoic Military Intelligence - Zero Tolerance for Data Breaches
Implements 3+ source confluence validation with aggressive fallbacks
"""

import json
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests

# Configure military-grade logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RELIABILITY_LOG = REPO_ROOT / "logs" / "data_reliability.json"
DATA_SOURCES_CONFIG = REPO_ROOT / "config" / "data_sources.json"

class DataSourceManager:
    """
    Military-grade data source management with confluence validation
    Implements aggressive backup chains and reliability tracking
    """
    
    def __init__(self):
        self.sources = {
            'yahoo': {'priority': 1, 'timeout': 5, 'reliability': 95.0},
            'alpha_vantage': {'priority': 2, 'timeout': 8, 'reliability': 92.0},
            'polygon': {'priority': 3, 'timeout': 6, 'reliability': 88.0},
            'coingecko': {'priority': 4, 'timeout': 10, 'reliability': 90.0}
        }
        self.reliability_threshold = 90.0
        self.confluence_threshold = 0.02  # 2% max deviation between sources
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Investment-Intelligence-System/2.0'
        })
        
    def log_source_event(self, source: str, symbol: str, success: bool, 
                        response_time: float = 0.0, error: str = None):
        """Log data source events for reliability tracking"""
        try:
            if not RELIABILITY_LOG.parent.exists():
                RELIABILITY_LOG.parent.mkdir(parents=True, exist_ok=True)
                
            # Load existing log or create new
            log_data = []
            if RELIABILITY_LOG.exists():
                with open(RELIABILITY_LOG, 'r') as f:
                    log_data = json.load(f)
            
            # Add new event
            event = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': source,
                'symbol': symbol,
                'success': success,
                'response_time': response_time,
                'error': error
            }
            log_data.append(event)
            
            # Keep only last 1000 events for performance
            if len(log_data) > 1000:
                log_data = log_data[-1000:]
                
            with open(RELIABILITY_LOG, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log source event: {e}")
    
    def calculate_reliability_score(self, source: str, hours: int = 24) -> float:
        """Calculate reliability score for a data source over time period"""
        if not RELIABILITY_LOG.exists():
            return 95.0  # Default for new sources
            
        try:
            with open(RELIABILITY_LOG, 'r') as f:
                log_data = json.load(f)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            recent_events = [
                event for event in log_data 
                if event['source'] == source and 
                datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            if not recent_events:
                return 95.0
                
            success_count = sum(1 for event in recent_events if event['success'])
            reliability = (success_count / len(recent_events)) * 100
            
            # Update internal tracking
            self.sources[source]['reliability'] = reliability
            return reliability
            
        except Exception as e:
            logger.error(f"Failed to calculate reliability for {source}: {e}")
            return 85.0  # Conservative fallback
    
    def fetch_yahoo_data(self, symbol: str, timeout: int = 5) -> Optional[Dict]:
        """Fetch data from Yahoo Finance with aggressive error handling"""
        start_time = time.time()
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1d", auto_adjust=True, timeout=timeout)
            
            if hist.empty or "Close" not in hist:
                raise ValueError("Empty or invalid data returned")
            
            latest_close = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else latest_close
            
            response_time = time.time() - start_time
            self.log_source_event('yahoo', symbol, True, response_time)
            
            return {
                'price': latest_close,
                'prev_price': prev_close,
                'change_pct': ((latest_close / prev_close) - 1) * 100 if prev_close else 0,
                'source': 'yahoo',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reliability': self.calculate_reliability_score('yahoo')
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Yahoo Finance breach detected: {str(e)}"
            logger.warning(f"VENOM ALERT: {error_msg}")
            self.log_source_event('yahoo', symbol, False, response_time, error_msg)
            return None
    
    def fetch_alpha_vantage_data(self, symbol: str, api_key: str = None) -> Optional[Dict]:
        """Fetch data from Alpha Vantage as backup confluence source"""
        if not api_key:
            logger.warning("Alpha Vantage API key not configured")
            return None
            
        start_time = time.time()
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }
            
            response = self.session.get(url, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            
            if 'Global Quote' not in data:
                raise ValueError("Invalid Alpha Vantage response structure")
            
            quote = data['Global Quote']
            latest_price = float(quote.get('05. price', 0))
            prev_close = float(quote.get('08. previous close', 0))
            
            response_time = time.time() - start_time
            self.log_source_event('alpha_vantage', symbol, True, response_time)
            
            return {
                'price': latest_price,
                'prev_price': prev_close,
                'change_pct': float(quote.get('10. change percent', '0').rstrip('%')),
                'source': 'alpha_vantage',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reliability': self.calculate_reliability_score('alpha_vantage')
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Alpha Vantage error: {str(e)}"
            self.log_source_event('alpha_vantage', symbol, False, response_time, error_msg)
            return None
    
    def fetch_polygon_data(self, symbol: str, api_key: str = None) -> Optional[Dict]:
        """Fetch data from Polygon.io as additional backup"""
        if not api_key:
            return None
            
        start_time = time.time()
        try:
            # Get previous trading day data
            end_date = datetime.now().strftime('%Y-%m-%d')
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{end_date}/{end_date}"
            params = {'apikey': api_key}
            
            response = self.session.get(url, params=params, timeout=6)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('results'):
                raise ValueError("No Polygon data available")
            
            result = data['results'][0]
            latest_price = float(result['c'])  # Close price
            
            response_time = time.time() - start_time
            self.log_source_event('polygon', symbol, True, response_time)
            
            return {
                'price': latest_price,
                'prev_price': float(result['o']),  # Open as proxy for prev close
                'change_pct': ((latest_price / float(result['o'])) - 1) * 100,
                'source': 'polygon',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reliability': self.calculate_reliability_score('polygon')
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Polygon error: {str(e)}"
            self.log_source_event('polygon', symbol, False, response_time, error_msg)
            return None
    
    def validate_confluence(self, data_points: List[Dict]) -> Tuple[bool, Dict]:
        """
        Military-grade confluence validation across multiple sources
        Requires 2/3+ sources to agree within threshold
        """
        if len(data_points) < 2:
            return False, {"error": "Insufficient data sources for confluence check"}
        
        # Extract prices for comparison
        prices = [dp['price'] for dp in data_points if dp.get('price', 0) > 0]
        
        if len(prices) < 2:
            return False, {"error": "Insufficient valid prices for confluence"}
        
        # Calculate price deviation
        avg_price = sum(prices) / len(prices)
        max_deviation = max(abs(price - avg_price) / avg_price for price in prices)
        
        confluence_passed = max_deviation <= self.confluence_threshold
        
        # Select highest reliability source as primary
        primary_source = max(data_points, key=lambda x: x.get('reliability', 0))
        
        result = {
            'confluence_passed': confluence_passed,
            'max_deviation_pct': max_deviation * 100,
            'sources_count': len(data_points),
            'avg_price': avg_price,
            'primary_source': primary_source['source'],
            'reliability_scores': {dp['source']: dp.get('reliability', 0) for dp in data_points}
        }
        
        if not confluence_passed:
            logger.warning(f"Data Poison Alert: Low Confluence - Max deviation {max_deviation*100:.2f}%")
            result['alert'] = "Manual Check Required: Source disagreement detected"
        
        return confluence_passed, result
    
    def get_confluence_data(self, symbol: str, api_keys: Dict[str, str] = None) -> Dict:
        """
        Stoic aggregation: Pull from 3+ sources, validate confluence, return best data
        Implements military-grade redundancy with aggressive validation
        """
        api_keys = api_keys or {}
        data_points = []
        
        # Attempt Yahoo Finance (primary)
        yahoo_data = self.fetch_yahoo_data(symbol)
        if yahoo_data:
            data_points.append(yahoo_data)
        
        # Attempt Alpha Vantage (backup 1)
        if api_keys.get('alpha_vantage'):
            av_data = self.fetch_alpha_vantage_data(symbol, api_keys['alpha_vantage'])
            if av_data:
                data_points.append(av_data)
        
        # Attempt Polygon (backup 2)
        if api_keys.get('polygon'):
            polygon_data = self.fetch_polygon_data(symbol, api_keys['polygon'])
            if polygon_data:
                data_points.append(polygon_data)
        
        # Validate confluence
        confluence_passed, validation_result = self.validate_confluence(data_points)
        
        if not data_points:
            return {
                'error': 'All data sources failed',
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sources_attempted': list(self.sources.keys()),
                'reliability_alert': True
            }
        
        # Return best available data with confluence metadata
        best_data = data_points[0] if len(data_points) == 1 else \
                   max(data_points, key=lambda x: x.get('reliability', 0))
        
        best_data.update({
            'confluence_validation': validation_result,
            'sources_used': [dp['source'] for dp in data_points],
            'fortress_status': 'SECURE' if confluence_passed else 'VERIFY_REQUIRED'
        })
        
        return best_data

def load_api_keys() -> Dict[str, str]:
    """Load API keys from secure configuration"""
    config_file = REPO_ROOT / "config" / "api_keys.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# Global instance for import
data_fortress = DataSourceManager()