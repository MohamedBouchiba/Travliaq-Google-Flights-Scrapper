# scripts/health_check.py
"""
Script de health check pour monitoring (cron job)
"""

import requests
import sys
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/health"

try:
    response = requests.get(API_URL, timeout=10)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "healthy":
            print(f"[{datetime.now()}] ✅ API healthy")
            sys.exit(0)
        else:
            print(f"[{datetime.now()}] ⚠️ API unhealthy: {data}")
            sys.exit(1)
    else:
        print(f"[{datetime.now()}] ❌ API error: {response.status_code}")
        sys.exit(1)

except Exception as e:
    print(f"[{datetime.now()}] ❌ Connection failed: {e}")
    sys.exit(1)