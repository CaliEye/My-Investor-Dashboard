// Configuration - Move sensitive data to environment variables or server-side
const CONFIG = {
  API_ENDPOINTS: {
    AI_INSIGHTS: './data/ai_insights.json',
    MARKET_DATA: './data/data.json',
    LOGS_SCANS: './logs/weekly_scans.md',
    LOGS_COMMANDS: './logs/command_log.md'
  },
  REFRESH_INTERVALS: {
    FAST_DATA: 60000,    // 1 minute for price data
    AI_DATA: 300000,     // 5 minutes for AI insights  
    LOG_DATA: 600000     // 10 minutes for logs
  },
  ALERT_SETTINGS: {
    CONFLUENCE_THRESHOLD: 8,
    COOLDOWN_MS: 5 * 60 * 1000,
    // Webhook URL should be fetched from server endpoint, not hardcoded
    WEBHOOK_ENDPOINT: '/api/alerts/webhook'
  }
};