"""
Automated Expiry Processor
Handles automatic expiration of signature requests and other time-sensitive items.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List

from app.models.signature_request import SignatureRequest, SignatureRequestStatus
from app.models.contract_draft import ContractDraft, DraftStatus
from app.services.email_service import email_service


class ExpiryProcessor:
    """Process expired signature requests and notify relevant parties"""

    def process_expired_signature_requests(self, db: Session) -> Dict:
        """
        Find and mark expired signature requests.
        Returns summary of actions taken.
        """
        now = datetime.utcnow()

        # Find all pending signature requests that are past their expiry date
        expired_requests = db.query(SignatureRequest).filter(
            SignatureRequest.status == SignatureRequestStatus.PENDING,
            SignatureRequest.expires_at.isnot(None),
            SignatureRequest.expires_at < now
        ).all()

        if not expired_requests:
            return {
                "expired_count": 0,
                "contracts_affected": 0,
                "notifications_sent": 0
            }

        # Group by contract for efficient processing
        contracts_affected = set()
        notifications_sent = 0

        for request in expired_requests:
            # Mark as expired
            request.status = SignatureRequestStatus.EXPIRED

            # Track affected contract
            contracts_affected.add(request.contract_draft_id)

            # Send notification to contract owner
            try:
                self._send_expiry_notification(request, db)
                notifications_sent += 1
            except Exception as e:
                print(f"Failed to send expiry notification for request {request.id}: {str(e)}")

        # Update contract statuses if needed
        for contract_id in contracts_affected:
            self._update_contract_status_after_expiry(contract_id, db)

        db.commit()

        return {
            "expired_count": len(expired_requests),
            "contracts_affected": len(contracts_affected),
            "notifications_sent": notifications_sent,
            "timestamp": now.isoformat()
        }

    def _send_expiry_notification(self, request: SignatureRequest, db: Session):
        """Send notification that a signature request has expired"""
        contract = request.contract_draft
        owner = request.requested_by

        email_service.send_signature_request_expired(
            owner_email=owner.email,
            owner_name=owner.full_name,
            contract_title=contract.title,
            signer_name=request.signer_name,
            signer_email=request.signer_email,
            contract_draft_id=str(contract.id),
            expired_at=request.expires_at
        )

    def _update_contract_status_after_expiry(self, contract_id, db: Session):
        """
        Update contract status if signature requests have expired.
        If some signatures collected but some expired, mark as needs attention.
        """
        draft = db.query(ContractDraft).filter(ContractDraft.id == contract_id).first()
        if not draft:
            return

        all_requests = db.query(SignatureRequest).filter(
            SignatureRequest.contract_draft_id == contract_id
        ).all()

        signed_count = sum(1 for req in all_requests if req.status == SignatureRequestStatus.SIGNED)
        expired_count = sum(1 for req in all_requests if req.status == SignatureRequestStatus.EXPIRED)
        pending_count = sum(1 for req in all_requests if req.status == SignatureRequestStatus.PENDING)

        # If all expired and none signed, revert to ready for signing
        if expired_count > 0 and signed_count == 0 and pending_count == 0:
            draft.status = DraftStatus.READY_FOR_SIGNING

        # If some signed but some expired, keep as partially signed
        # (owner will need to resend expired requests)

    def cleanup_old_expired_requests(self, db: Session, days_old: int = 90) -> int:
        """
        Clean up very old expired requests to keep database tidy.
        Returns number of requests deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        old_expired = db.query(SignatureRequest).filter(
            SignatureRequest.status == SignatureRequestStatus.EXPIRED,
            SignatureRequest.expires_at < cutoff_date
        ).all()

        count = len(old_expired)

        for request in old_expired:
            db.delete(request)

        db.commit()

        return count


# Singleton instance
expiry_processor = ExpiryProcessor()
