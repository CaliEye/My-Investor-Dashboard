# Enhanced Alert System Backend
# This should be added to your Python backend to handle alerts securely

import os
import requests
import time
from datetime import datetime
from typing import Dict, Any

class SecureAlertManager:
    def __init__(self):
        # Load webhook URL from environment variable (not in client code)
        self.webhook_url = os.getenv('LINDY_WEBHOOK_URL')
        self.alert_cooldown = 5 * 60  # 5 minutes
        self.last_alert_times = {}
        
    def should_send_alert(self, alert_type: str, score: int) -> bool:
        """Check if alert should be sent based on cooldown and score"""
        if score < 8:
            return False
            
        now = time.time()
        last_alert = self.last_alert_times.get(alert_type, 0)
        
        return (now - last_alert) >= self.alert_cooldown
    
    def send_confluence_alert(self, confluence_data: Dict[str, Any]) -> bool:
        """Send confluence alert via webhook"""
        try:
            if not self.webhook_url:
                print("Warning: Webhook URL not configured")
                return False
                
            score = confluence_data.get('confluence_score', 0)
            if not self.should_send_alert('confluence', score):
                return False
            
            payload = {
                'asset': 'BTC-DASHBOARD',
                'confidence': score,
                'signal': confluence_data.get('dominant_signal', 'neutral'),
                'timeframe': 'multi-source',
                'notes': f"5-source confluence: {confluence_data.get('agreement_pct', 0)}% agreement",
                'timestamp': datetime.utcnow().isoformat(),
                'sources': len(confluence_data.get('source_breakdown', []))
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.last_alert_times['confluence'] = time.time()
                print(f"Alert sent successfully for confluence score {score}")
                return True
            else:
                print(f"Alert failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Alert error: {e}")
            return False