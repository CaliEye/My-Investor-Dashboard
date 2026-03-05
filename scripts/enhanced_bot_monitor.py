#!/usr/bin/env python3
"""
Enhanced Bot Performance Monitor - Military Intelligence System
Real-time threshold alerts for drawdown/win rate with confluence scoring
Implements: Aggressive monitoring, predictive alerts, performance shields
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
BOTS_FILE = REPO_ROOT / "data" / "bots_data.json"
MARKET_FILE = REPO_ROOT / "data" / "data.json"
BOT_ALERTS_LOG = REPO_ROOT / "logs" / "bot_performance_alerts.json"
BOT_MONITORING_REPORT = REPO_ROOT / "logs" / "bot_monitoring_report.json"

# Military-grade thresholds for bot performance
ALERT_THRESHOLDS = {
    'max_drawdown_pct': {
        'warning': 5.0,      # 5% drawdown triggers warning
        'critical': 10.0,    # 10% drawdown triggers critical alert
        'emergency': 20.0    # 20% drawdown triggers emergency shutdown
    },
    'win_rate_pct': {
        'warning': 45.0,     # Win rate below 45% triggers warning
        'critical': 35.0,    # Win rate below 35% triggers critical alert
        'emergency': 25.0    # Win rate below 25% triggers emergency review
    },
    'weekly_pnl_pct': {
        'warning': -2.0,     # Weekly loss > 2% triggers warning
        'critical': -5.0,    # Weekly loss > 5% triggers critical alert
        'emergency': -10.0   # Weekly loss > 10% triggers emergency halt
    },
    'confluence_score': {
        'warning': 4,        # Confluence below 4/10 triggers warning
        'critical': 3,       # Confluence below 3/10 triggers critical alert
        'emergency': 2       # Confluence below 2/10 triggers emergency check
    }
}

PERFORMANCE_CATEGORIES = {
    'ELITE': {'min_win_rate': 65, 'max_drawdown': 3.0, 'min_confluence': 7},
    'SUPERIOR': {'min_win_rate': 55, 'max_drawdown': 5.0, 'min_confluence': 6},
    'OPERATIONAL': {'min_win_rate': 45, 'max_drawdown': 8.0, 'min_confluence': 5},
    'DEGRADED': {'min_win_rate': 35, 'max_drawdown': 12.0, 'min_confluence': 4},
    'COMPROMISED': {'min_win_rate': 0, 'max_drawdown': float('inf'), 'min_confluence': 0}
}

class BotPerformanceMonitor:
    """Military-grade bot performance monitoring with predictive alerts"""
    
    def __init__(self):
        self.alerts_history = self.load_alerts_history()
        
    def load_alerts_history(self) -> List[Dict]:
        """Load historical alerts for trend analysis"""
        if BOT_ALERTS_LOG.exists():
            try:
                with open(BOT_ALERTS_LOG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load alerts history: {e}")
        return []
    
    def save_alert(self, alert: Dict):
        """Save alert to persistent log"""
        self.alerts_history.append(alert)
        
        # Keep only last 500 alerts for performance
        if len(self.alerts_history) > 500:
            self.alerts_history = self.alerts_history[-500:]
        
        try:
            if not BOT_ALERTS_LOG.parent.exists():
                BOT_ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
            
            with open(BOT_ALERTS_LOG, 'w') as f:
                json.dump(self.alerts_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
    
    def categorize_bot_performance(self, bot: Dict) -> str:
        """Categorize bot performance level"""
        win_rate = bot.get('win_rate_pct', 0)
        drawdown = bot.get('max_drawdown_pct', 0)
        confluence = bot.get('confluence_score', 0)
        
        for category, thresholds in PERFORMANCE_CATEGORIES.items():
            if (win_rate >= thresholds['min_win_rate'] and 
                drawdown <= thresholds['max_drawdown'] and
                confluence >= thresholds['min_confluence']):
                return category
        
        return 'COMPROMISED'
    
    def check_bot_thresholds(self, bot: Dict) -> List[Dict]:
        """Check bot against all performance thresholds"""
        alerts = []
        bot_name = bot.get('name', 'Unknown Bot')
        
        for metric, thresholds in ALERT_THRESHOLDS.items():
            value = bot.get(metric, 0)
            
            # Determine alert level
            alert_level = None
            if metric in ['max_drawdown_pct', 'weekly_pnl_pct']:
                # For drawdown and PnL, higher absolute values are worse
                if metric == 'weekly_pnl_pct':
                    # Negative PnL check
                    if value <= thresholds['emergency']:
                        alert_level = 'EMERGENCY'
                    elif value <= thresholds['critical']:
                        alert_level = 'CRITICAL'
                    elif value <= thresholds['warning']:
                        alert_level = 'WARNING'
                else:
                    # Drawdown check
                    if value >= thresholds['emergency']:
                        alert_level = 'EMERGENCY'
                    elif value >= thresholds['critical']:
                        alert_level = 'CRITICAL'
                    elif value >= thresholds['warning']:
                        alert_level = 'WARNING'
                        
            else:
                # For win rate and confluence, lower values are worse
                if value <= thresholds['emergency']:
                    alert_level = 'EMERGENCY'
                elif value <= thresholds['critical']:
                    alert_level = 'CRITICAL'
                elif value <= thresholds['warning']:
                    alert_level = 'WARNING'
            
            if alert_level:
                alert = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'bot_name': bot_name,
                    'metric': metric,
                    'value': value,
                    'threshold': thresholds[alert_level.lower()],
                    'alert_level': alert_level,
                    'message': f"{bot_name}: {metric} = {value} (threshold: {thresholds[alert_level.lower()]})",
                    'category': self.categorize_bot_performance(bot)
                }
                alerts.append(alert)
        
        return alerts
    
    def calculate_bot_health_score(self, bot: Dict) -> float:
        """Calculate comprehensive health score (0-100)"""
        win_rate = bot.get('win_rate_pct', 0)
        drawdown = bot.get('max_drawdown_pct', 0)
        pnl = bot.get('weekly_pnl_pct', 0)
        confluence = bot.get('confluence_score', 0)
        
        # Normalize metrics to 0-100 scale
        win_rate_score = min(100, max(0, win_rate))
        
        # Drawdown penalty (invert and cap at 100)
        drawdown_score = max(0, 100 - (drawdown * 10))
        
        # PnL contribution (cap negative impact)
        pnl_score = 50 + (pnl * 10)
        pnl_score = min(100, max(0, pnl_score))
        
        # Confluence score (convert from 1-10 to 0-100)
        confluence_score = confluence * 10
        
        # Weighted average
        health_score = (
            win_rate_score * 0.3 +      # 30% weight on win rate
            drawdown_score * 0.35 +     # 35% weight on drawdown control
            pnl_score * 0.2 +          # 20% weight on PnL
            confluence_score * 0.15     # 15% weight on confluence
        )
        
        return round(health_score, 2)
    
    def analyze_bot_trends(self, bot_name: str, days: int = 7) -> Dict:
        """Analyze performance trends for predictive alerts"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        bot_alerts = [
            alert for alert in self.alerts_history
            if alert.get('bot_name') == bot_name and
            datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
        
        if not bot_alerts:
            return {'trend': 'STABLE', 'alert_frequency': 0, 'degradation_risk': 'LOW'}
        
        # Calculate alert frequency
        alert_frequency = len(bot_alerts) / days
        
        # Analyze alert severity trends
        emergency_alerts = len([a for a in bot_alerts if a.get('alert_level') == 'EMERGENCY'])
        critical_alerts = len([a for a in bot_alerts if a.get('alert_level') == 'CRITICAL'])
        
        # Determine trend
        if emergency_alerts > 0:
            trend = 'DETERIORATING'
            degradation_risk = 'CRITICAL'
        elif critical_alerts >= 2:
            trend = 'DEGRADING'
            degradation_risk = 'HIGH'
        elif alert_frequency > 1.0:  # More than 1 alert per day
            trend = 'UNSTABLE'
            degradation_risk = 'MEDIUM'
        else:
            trend = 'STABLE'
            degradation_risk = 'LOW'
        
        return {
            'trend': trend,
            'alert_frequency': round(alert_frequency, 2),
            'degradation_risk': degradation_risk,
            'emergency_alerts_last_week': emergency_alerts,
            'critical_alerts_last_week': critical_alerts,
            'total_alerts_last_week': len(bot_alerts)
        }
    
    def generate_performance_recommendations(self, bot: Dict) -> List[str]:
        """Generate actionable recommendations based on bot performance"""
        recommendations = []
        category = self.categorize_bot_performance(bot)
        health_score = self.calculate_bot_health_score(bot)
        
        win_rate = bot.get('win_rate_pct', 0)
        drawdown = bot.get('max_drawdown_pct', 0)
        pnl = bot.get('weekly_pnl_pct', 0)
        confluence = bot.get('confluence_score', 0)
        
        if category == 'COMPROMISED':
            recommendations.append("URGENT: Bot performance critically compromised - Consider immediate suspension")
        
        if drawdown > 15:
            recommendations.append(f"CRITICAL: Excessive drawdown ({drawdown}%) - Reduce position size or halt trading")
        elif drawdown > 8:
            recommendations.append(f"WARNING: High drawdown risk at {drawdown}% - Monitor risk management")
        
        if win_rate < 35:
            recommendations.append(f"ALERT: Low win rate ({win_rate}%) - Review strategy parameters")
        
        if pnl < -5:
            recommendations.append(f"CRITICAL: Severe weekly loss ({pnl}%) - Emergency review required")
        
        if confluence < 4:
            recommendations.append(f"WARNING: Low market confluence ({confluence}/10) - Consider reducing exposure")
        
        if health_score < 30:
            recommendations.append(f"EMERGENCY: Health score critically low ({health_score}/100)")
        elif health_score < 50:
            recommendations.append(f"CAUTION: Health score degraded ({health_score}/100)")
        
        # Positive recommendations for strong performers
        if category == 'ELITE' and health_score > 80:
            recommendations.append(f"EXCELLENT: Elite performance maintained - Consider position increase")
        
        if not recommendations:
            recommendations.append("OPERATIONAL: Performance within acceptable parameters")
        
        return recommendations

def load_data_files() -> Tuple[Dict, Dict]:
    """Load bots and market data files"""
    bots_data = {}
    market_data = {}
    
    try:
        if BOTS_FILE.exists():
            with open(BOTS_FILE, 'r') as f:
                bots_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load bots data: {e}")
    
    try:
        if MARKET_FILE.exists():
            with open(MARKET_FILE, 'r') as f:
                market_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load market data: {e}")
    
    return bots_data, market_data

def main():
    """Generate comprehensive bot monitoring report with real-time alerts"""
    logger.info("Initializing Enhanced Bot Performance Monitor...")
    
    monitor = BotPerformanceMonitor()
    bots_data, market_data = load_data_files()
    
    bots = bots_data.get('bots', [])
    if not bots:
        logger.error("No bot data available for monitoring")
        return
    
    # Generate comprehensive monitoring report
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'monitoring_status': 'ACTIVE',
        'bots_monitored': len(bots),
        'bot_analysis': [],
        'system_alerts': [],
        'fleet_summary': {},
        'recommendations': []
    }
    
    all_alerts = []
    health_scores = []
    
    # Analyze each bot
    for bot in bots:
        bot_name = bot.get('name', 'Unknown')
        logger.info(f"Analyzing bot: {bot_name}")
        
        # Check thresholds and generate alerts
        bot_alerts = monitor.check_bot_thresholds(bot)
        all_alerts.extend(bot_alerts)
        
        # Calculate health metrics
        health_score = monitor.calculate_bot_health_score(bot)
        health_scores.append(health_score)
        category = monitor.categorize_bot_performance(bot)
        trends = monitor.analyze_bot_trends(bot_name)
        recommendations = monitor.generate_performance_recommendations(bot)
        
        bot_analysis = {
            'name': bot_name,
            'category': category,
            'health_score': health_score,
            'alerts_count': len(bot_alerts),
            'trend_analysis': trends,
            'metrics': {
                'win_rate_pct': bot.get('win_rate_pct', 0),
                'max_drawdown_pct': bot.get('max_drawdown_pct', 0),
                'weekly_pnl_pct': bot.get('weekly_pnl_pct', 0),
                'confluence_score': bot.get('confluence_score', 0)
            },
            'recommendations': recommendations[:3]  # Top 3 recommendations
        }
        
        report['bot_analysis'].append(bot_analysis)
        
        # Save critical alerts
        for alert in bot_alerts:
            if alert['alert_level'] in ['CRITICAL', 'EMERGENCY']:
                monitor.save_alert(alert)
                logger.warning(f"ALERT: {alert['message']}")
    
    # Fleet summary
    if health_scores:
        report['fleet_summary'] = {
            'average_health_score': round(statistics.mean(health_scores), 2),
            'best_performer': max(report['bot_analysis'], key=lambda x: x['health_score'])['name'],
            'worst_performer': min(report['bot_analysis'], key=lambda x: x['health_score'])['name'],
            'bots_in_warning': len([b for b in report['bot_analysis'] if b['category'] in ['DEGRADED', 'COMPROMISED']]),
            'elite_bots': len([b for b in report['bot_analysis'] if b['category'] == 'ELITE']),
            'total_alerts': len(all_alerts),
            'critical_alerts': len([a for a in all_alerts if a['alert_level'] in ['CRITICAL', 'EMERGENCY']])
        }
    
    # System-level recommendations
    critical_count = report['fleet_summary'].get('critical_alerts', 0)
    avg_health = report['fleet_summary'].get('average_health_score', 0)
    
    if critical_count > 0:
        report['recommendations'].append(f"URGENT: {critical_count} critical alerts require immediate attention")
    
    if avg_health < 50:
        report['recommendations'].append("FLEET DEGRADATION: Average health below 50% - Review strategy parameters")
    
    if report['fleet_summary'].get('bots_in_warning', 0) > len(bots) * 0.5:
        report['recommendations'].append("SYSTEM ALERT: Majority of bots showing degraded performance")
    
    if not report['recommendations']:
        report['recommendations'].append("FLEET STATUS: All systems operational within acceptable parameters")
    
    # Save monitoring report
    try:
        if not BOT_MONITORING_REPORT.parent.exists():
            BOT_MONITORING_REPORT.parent.mkdir(parents=True, exist_ok=True)
        
        with open(BOT_MONITORING_REPORT, 'w') as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save monitoring report: {e}")
    
    # Console summary
    print(f"\n=== BOT PERFORMANCE MONITOR ===")
    print(f"Fleet Health: {report['fleet_summary'].get('average_health_score', 0)}/100")
    print(f"Critical Alerts: {report['fleet_summary'].get('critical_alerts', 0)}")
    print(f"Elite Bots: {report['fleet_summary'].get('elite_bots', 0)}/{len(bots)}")
    print(f"Report saved to: {BOT_MONITORING_REPORT}")
    
    return report

if __name__ == "__main__":
    main()