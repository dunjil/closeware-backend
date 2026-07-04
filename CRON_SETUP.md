# Automated Expiry Processing Setup

## Overview

Closeware automatically processes expired signature requests to:
- Mark expired requests as `EXPIRED`
- Update contract statuses appropriately
- Notify contract owners when signatures expire
- Clean up old expired requests

## Setup Options

### Option 1: System Cron (Linux/Mac)

**1. Set the cron secret token in your .env:**
```bash
CRON_SECRET_TOKEN=your-secure-random-token-here
```

**2. Add to crontab:**
```bash
crontab -e
```

**3. Add these lines:**
```bash
# Process expired signature requests every hour
0 * * * * curl -X POST -H "X-Cron-Token: your-secure-random-token-here" https://api.closeware.com/api/v1/maintenance/process-expired-signatures

# Clean up old expired requests weekly (Sunday at 2am)
0 2 * * 0 curl -X POST -H "X-Cron-Token: your-secure-random-token-here" "https://api.closeware.com/api/v1/maintenance/cleanup-old-expired-requests?days_old=90"
```

Replace `https://api.closeware.com` with your actual API URL.

---

### Option 2: Cloud Cron Services

#### **Vercel Cron (Recommended for Vercel deployments)**

Add to `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/cron/process-expiry",
      "schedule": "0 * * * *"
    }
  ]
}
```

Create `/api/cron/process-expiry.ts`:
```typescript
import { NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return new Response('Unauthorized', { status: 401 });
  }

  const response = await fetch(
    `${process.env.BACKEND_URL}/api/v1/maintenance/process-expired-signatures`,
    {
      method: 'POST',
      headers: {
        'X-Cron-Token': process.env.CRON_SECRET_TOKEN!
      }
    }
  );

  const data = await response.json();
  return Response.json(data);
}
```

#### **GitHub Actions (Free for public/private repos)**

Create `.github/workflows/expiry-cron.yml`:
```yaml
name: Process Expired Signatures

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:  # Manual trigger

jobs:
  process-expiry:
    runs-on: ubuntu-latest
    steps:
      - name: Call expiry endpoint
        run: |
          curl -X POST \
            -H "X-Cron-Token: ${{ secrets.CRON_SECRET_TOKEN }}" \
            https://api.closeware.com/api/v1/maintenance/process-expired-signatures
```

Add `CRON_SECRET_TOKEN` to GitHub Secrets.

#### **Railway/Render/Fly.io (Built-in Cron)**

Most platforms support cron jobs. Example for Railway:

Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE"
  },
  "crons": [
    {
      "name": "process-expiry",
      "schedule": "0 * * * *",
      "command": "curl -X POST -H 'X-Cron-Token: $CRON_SECRET_TOKEN' http://localhost:$PORT/api/v1/maintenance/process-expired-signatures"
    }
  ]
}
```

---

### Option 3: Python APScheduler (Built-in)

**Add to requirements.txt:**
```
apscheduler==3.10.4
```

**Create `app/scheduler.py`:**
```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.base import SessionLocal
from app.services.expiry_processor import expiry_processor

scheduler = BackgroundScheduler()

def process_expiry_job():
    """Background job to process expired signature requests"""
    db = SessionLocal()
    try:
        result = expiry_processor.process_expired_signature_requests(db)
        print(f"Expiry processing completed: {result}")
    except Exception as e:
        print(f"Expiry processing failed: {str(e)}")
    finally:
        db.close()

def start_scheduler():
    """Start the background scheduler"""
    # Run every hour
    scheduler.add_job(process_expiry_job, 'interval', hours=1, id='expiry_processor')
    
    # Cleanup old requests weekly
    scheduler.add_job(
        lambda: cleanup_job(),
        'cron',
        day_of_week='sun',
        hour=2,
        id='expiry_cleanup'
    )
    
    scheduler.start()

def cleanup_job():
    db = SessionLocal()
    try:
        count = expiry_processor.cleanup_old_expired_requests(db, days_old=90)
        print(f"Cleanup completed: {count} old requests deleted")
    finally:
        db.close()
```

**Update `app/main.py`:**
```python
from app.scheduler import start_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()
```

---

## Monitoring

### Health Check Endpoint

Check system status:
```bash
curl https://api.closeware.com/api/v1/maintenance/health-check
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2026-07-04T12:00:00",
  "signature_requests": {
    "pending": 15,
    "expired": 3,
    "needs_expiry_processing": 2
  }
}
```

If `needs_expiry_processing` > 0, the cron job needs to run.

---

## Testing

### Manual Trigger (Development)

```bash
# Without token (development mode - no CRON_SECRET_TOKEN set)
curl -X POST http://localhost:8000/api/v1/maintenance/process-expired-signatures

# With token (production)
curl -X POST \
  -H "X-Cron-Token: your-secret-token" \
  https://api.closeware.com/api/v1/maintenance/process-expired-signatures
```

### Expected Response

```json
{
  "success": true,
  "message": "Expiry processing completed",
  "summary": {
    "expired_count": 5,
    "contracts_affected": 3,
    "notifications_sent": 5,
    "timestamp": "2026-07-04T12:00:00"
  }
}
```

---

## Security

1. **Always set `CRON_SECRET_TOKEN`** in production
2. Use a long, random token (32+ characters)
3. Rotate token if compromised
4. Monitor access logs for unauthorized attempts
5. Use HTTPS only in production

Generate secure token:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Troubleshooting

**Problem:** Cron job not running
- Check cron logs: `grep CRON /var/log/syslog`
- Verify cron service running: `sudo service cron status`
- Check token matches between .env and crontab

**Problem:** Signatures not being marked expired
- Check health endpoint for `needs_expiry_processing`
- Verify signature requests have `expires_at` set
- Check database timezone matches server timezone

**Problem:** Emails not sending
- Check `MAILERSEND_API_KEY` is set
- Verify email service logs
- Test email service separately

---

## Recommended Schedule

| Task | Frequency | Cron Expression |
|------|-----------|-----------------|
| Process expired requests | Every hour | `0 * * * *` |
| Cleanup old expired | Weekly | `0 2 * * 0` |
| Health check | Every 15 min | `*/15 * * * *` |

---

## Production Checklist

- [ ] `CRON_SECRET_TOKEN` set in environment
- [ ] Cron job configured and running
- [ ] Health check monitoring setup
- [ ] Email notifications tested
- [ ] Logs being monitored
- [ ] Backup cron service configured (redundancy)
