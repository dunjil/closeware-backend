"""
Maintenance and Background Job Endpoints
These endpoints should be called by cron jobs or scheduled tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.db.base import get_db
from app.services.expiry_processor import expiry_processor

router = APIRouter()


def verify_cron_token(x_cron_token: Optional[str] = Header(None)):
    """
    Verify that the request is from an authorized cron job.
    Set CRON_SECRET_TOKEN in environment variables for security.
    """
    expected_token = os.getenv("CRON_SECRET_TOKEN")

    # If no token is set in env, allow access (development mode)
    if not expected_token:
        return True

    # In production, require valid token
    if not x_cron_token or x_cron_token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized - Invalid or missing cron token"
        )

    return True


@router.post("/process-expired-signatures")
async def process_expired_signature_requests(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_cron_token)
):
    """
    Process expired signature requests.

    This endpoint should be called by a cron job periodically (e.g., every hour).

    Cron setup example (runs every hour):
    0 * * * * curl -X POST -H "X-Cron-Token: your-secret-token" https://api.closeware.com/api/v1/maintenance/process-expired-signatures

    Or using Python APScheduler:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_expiry, 'interval', hours=1)
    scheduler.start()
    """
    try:
        result = expiry_processor.process_expired_signature_requests(db)

        return {
            "success": True,
            "message": "Expiry processing completed",
            "summary": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Expiry processing failed: {str(e)}")


@router.post("/cleanup-old-expired-requests")
async def cleanup_old_expired_requests(
    days_old: int = 90,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_cron_token)
):
    """
    Clean up expired signature requests older than specified days.
    Helps keep database tidy.

    Should be run less frequently (e.g., weekly or monthly).

    Cron setup example (runs weekly on Sunday at 2am):
    0 2 * * 0 curl -X POST -H "X-Cron-Token: your-secret-token" "https://api.closeware.com/api/v1/maintenance/cleanup-old-expired-requests?days_old=90"
    """
    try:
        deleted_count = expiry_processor.cleanup_old_expired_requests(db, days_old)

        return {
            "success": True,
            "message": f"Cleanup completed - {deleted_count} old expired requests deleted",
            "deleted_count": deleted_count,
            "days_old_threshold": days_old
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/health-check")
async def maintenance_health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for monitoring.
    No authentication required.
    """
    from app.models.signature_request import SignatureRequest, SignatureRequestStatus
    from datetime import datetime

    # Get counts of signature requests by status
    now = datetime.utcnow()

    pending_count = db.query(SignatureRequest).filter(
        SignatureRequest.status == SignatureRequestStatus.PENDING
    ).count()

    expired_count = db.query(SignatureRequest).filter(
        SignatureRequest.status == SignatureRequestStatus.EXPIRED
    ).count()

    # Count requests that SHOULD be expired but aren't marked yet
    needs_expiry = db.query(SignatureRequest).filter(
        SignatureRequest.status == SignatureRequestStatus.PENDING,
        SignatureRequest.expires_at.isnot(None),
        SignatureRequest.expires_at < now
    ).count()

    return {
        "status": "healthy",
        "timestamp": now.isoformat(),
        "signature_requests": {
            "pending": pending_count,
            "expired": expired_count,
            "needs_expiry_processing": needs_expiry
        }
    }
