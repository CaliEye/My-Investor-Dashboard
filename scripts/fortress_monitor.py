#!/usr/bin/env python3
"""
Data Fortress Reliability Monitor
Real-time monitoring of data source health and confluence validation
Military-grade visibility into fortress operations
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RELIABILITY_LOG = REPO_ROOT / "logs" / "data_reliability.json"
REPORT_FILE = REPO_ROOT / "logs" / "fortress_status_report.json"

def load_reliability_log() -> List[Dict]:
    """Load reliability log data"""
    if not RELIABILITY_LOG.exists():
        return []
    
    try:
        with open(RELIABILITY_LOG, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load reliability log: {e}")
        return []

def calculate_source_health(events: List[Dict], source: str, hours: int = 24) -> Dict:
    """Calculate health metrics for a data source"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    source_events = [
        event for event in events 
        if event.get('source') == source and 
        datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')) > cutoff_time
    ]
    
    if not source_events:
        return {
            'source': source,
            'status': 'NO_DATA',
            'reliability_pct': 0,
            'events_count': 0,
            'avg_response_time': 0,
            'last_success': None,
            'last_failure': None
        }
    
    success_events = [e for e in source_events if e.get('success', False)]
    failure_events = [e for e in source_events if not e.get('success', True)]
    
    reliability_pct = (len(success_events) / len(source_events)) * 100
    avg_response_time = sum(e.get('response_time', 0) for e in source_events) / len(source_events)
    
    last_success = None
    last_failure = None
    
    if success_events:
        last_success = max(success_events, key=lambda x: x['timestamp'])['timestamp']
    if failure_events:
        last_failure = max(failure_events, key=lambda x: x['timestamp'])['timestamp']
    
    # Determine status
    if reliability_pct >= 95:
        status = 'SECURE'
    elif reliability_pct >= 85:
        status = 'DEGRADED'
    else:
        status = 'COMPROMISED'
    
    return {
        'source': source,
        'status': status,
        'reliability_pct': round(reliability_pct, 2),
        'events_count': len(source_events),
        'success_count': len(success_events),
        'failure_count': len(failure_events),
        'avg_response_time': round(avg_response_time, 3),
        'last_success': last_success,
        'last_failure': last_failure,
        'recent_errors': [e.get('error') for e in failure_events[-5:] if e.get('error')]
    }

def generate_fortress_status() -> Dict:
    """Generate comprehensive fortress status report"""
    events = load_reliability_log()
    
    sources = ['yahoo', 'alpha_vantage', 'polygon', 'coingecko']
    source_health = {}
    
    for source in sources:
        health = calculate_source_health(events, source)
        source_health[source] = health
    
    # Calculate overall fortress health
    active_sources = [h for h in source_health.values() if h['events_count'] > 0]
    if not active_sources:
        fortress_status = 'OFFLINE'
        fortress_reliability = 0
    else:
        fortress_reliability = sum(h['reliability_pct'] for h in active_sources) / len(active_sources)
        if fortress_reliability >= 90:
            fortress_status = 'FORTRESS_SECURE'
        elif fortress_reliability >= 75:
            fortress_status = 'OPERATIONAL'
        else:
            fortress_status = 'ALERT_REQUIRED'
    
    # Recent activity summary
    recent_events = [
        e for e in events 
        if datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > 
        datetime.now(timezone.utc) - timedelta(hours=1)
    ]
    
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'fortress_status': fortress_status,
        'fortress_reliability_pct': round(fortress_reliability, 2),
        'active_sources_count': len(active_sources),
        'source_health': source_health,
        'recent_activity': {
            'events_last_hour': len(recent_events),
            'success_rate_last_hour': (
                sum(1 for e in recent_events if e.get('success', False)) / len(recent_events) * 100
                if recent_events else 0
            )
        },
        'recommendations': generate_recommendations(source_health),
        'next_check': (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    }

def generate_recommendations(source_health: Dict) -> List[str]:
    """Generate actionable recommendations based on fortress status"""
    recommendations = []
    
    for source, health in source_health.items():
        if health['status'] == 'COMPROMISED':
            recommendations.append(f"CRITICAL: {source} reliability below 85% - Check API limits/keys")
        elif health['status'] == 'DEGRADED':
            recommendations.append(f"WARNING: {source} reliability degraded - Monitor closely")
        elif health['events_count'] == 0:
            recommendations.append(f"INFO: {source} not configured - Add API key for redundancy")
    
    # Check for single points of failure
    active_secure_sources = [
        s for s, h in source_health.items() 
        if h['status'] == 'SECURE' and h['events_count'] > 0
    ]
    
    if len(active_secure_sources) < 2:
        recommendations.append("STRATEGIC: Configure additional API sources for fortress redundancy")
    
    if not recommendations:
        recommendations.append("FORTRESS_SECURE: All systems operational - Maintain vigilance")
    
    return recommendations

def main():
    """Generate and save fortress status report"""
    logger.info("Generating Data Fortress Status Report...")
    
    try:
        status = generate_fortress_status()
        
        # Ensure logs directory exists
        if not REPORT_FILE.parent.exists():
            REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Save report
        with open(REPORT_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        
        # Log summary
        logger.info(f"Fortress Status: {status['fortress_status']}")
        logger.info(f"Overall Reliability: {status['fortress_reliability_pct']}%")
        logger.info(f"Active Sources: {status['active_sources_count']}")
        
        for rec in status['recommendations'][:3]:  # Show top 3 recommendations
            logger.info(f"Recommendation: {rec}")
        
        print(f"\n=== DATA FORTRESS STATUS ===")
        print(f"Status: {status['fortress_status']}")
        print(f"Reliability: {status['fortress_reliability_pct']}%")
        print(f"Active Sources: {status['active_sources_count']}")
        print(f"\nFull report saved to: {REPORT_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to generate fortress status: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())