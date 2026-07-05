#!/usr/bin/env python3
"""
Simple script to check Anthropic API usage and alert if over threshold.
Run this daily or weekly during POC testing.

Usage:
    python scripts/check_api_usage.py
"""

import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ALERT_THRESHOLD = 15.00  # Alert when spending exceeds $15 (out of $20)
WARNING_THRESHOLD = 10.00  # Warning at $10

def get_usage_estimate():
    """
    Note: Anthropic API doesn't provide a usage endpoint yet.
    This is a placeholder for manual tracking.

    For now, manually update CURRENT_SPEND below after checking:
    https://console.anthropic.com/settings/usage
    """

    # TODO: Update this manually after checking console
    CURRENT_SPEND = 0.00  # Update this after checking the dashboard

    return CURRENT_SPEND

def check_usage():
    print("=" * 60)
    print("ANTHROPIC API USAGE CHECK")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Manual check reminder
    print("📊 Please check your usage manually at:")
    print("   https://console.anthropic.com/settings/usage")
    print()

    current_spend = get_usage_estimate()

    print(f"💰 Current Spend (manual update): ${current_spend:.2f}")
    print(f"⚠️  Warning Threshold: ${WARNING_THRESHOLD:.2f}")
    print(f"🚨 Alert Threshold: ${ALERT_THRESHOLD:.2f}")
    print()

    if current_spend >= ALERT_THRESHOLD:
        print("🚨 ALERT: You've exceeded $15! Consider adding more credits.")
        print("   Remaining budget: $", 20 - current_spend)
        return False
    elif current_spend >= WARNING_THRESHOLD:
        print("⚠️  WARNING: You've used over $10 of your POC budget.")
        print("   Remaining: $", 20 - current_spend)
        return True
    else:
        print(f"✅ Usage looks good. ${20 - current_spend:.2f} remaining.")
        return True

    print()
    print("=" * 60)

if __name__ == "__main__":
    check_usage()
