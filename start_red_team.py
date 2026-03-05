"""
Start Anti-AI Red Team Continuous Operations
Launches the market defense system for 24/7 monitoring
"""

from scripts.anti_ai_red_team import ContinuousOperationsBrain
import threading
import time
import signal
import sys

def signal_handler(sig, frame):
    print('\n[ANTI-AI] Red Team shutting down gracefully...')
    sys.exit(0)

def main():
    # Set up graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("[ANTI-AI] RED TEAM & MARKET DEFENSE SYSTEM")
    print("=" * 60)
    print("[BOOT] Initializing continuous operations...")
    
    # Initialize the brain
    operations_brain = ContinuousOperationsBrain()
    
    print("[OK] Operations brain online")
    print("[SCAN] Starting continuous monitoring...")
    print("[DEFENSE] Real-time defense against:")
    print("   • Market Makers manipulation")
    print("   • Hedge Fund coordinated attacks")
    print("   • Whale pump/dump schemes")
    print("   • Insider trading exploitation")
    print("   • Rug pull attempts")
    print("   • Scam and fraud detection")
    print("\n[STATUS] DEFENSE SYSTEMS ARMED")
    print("Press Ctrl+C to stop monitoring\n")
    
    # Start continuous operations
    try:
        operations_brain.continuous_operations()
    except KeyboardInterrupt:
        print('\n[ANTI-AI] Shutting down market defense system...')
        print('[OK] All monitoring stopped safely')

if __name__ == "__main__":
    main()