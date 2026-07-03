from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.db.base import get_db
from app.models.contract_status_history import ContractStatusHistory
from app.models.contract_draft import ContractDraft
from app.models.internal_review import InternalReview
from app.models.signature_request import SignatureRequest
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


class StatusChangeResponse(BaseModel):
    id: UUID
    old_status: str | None
    new_status: str
    changed_by_name: str
    changed_by_email: str
    reason: str | None
    changed_at: datetime
    ip_address: str | None

    class Config:
        from_attributes = True


class ReviewHistoryResponse(BaseModel):
    id: UUID
    reviewer_name: str
    reviewer_email: str
    action: str
    comments: str | None
    draft_version: int
    reviewed_at: datetime
    ip_address: str | None

    class Config:
        from_attributes = True


class SignatureHistoryResponse(BaseModel):
    id: UUID
    signer_name: str
    signer_email: str
    signer_role: str
    status: str
    requested_at: datetime
    signed_at: datetime | None
    declined_at: datetime | None

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    contract_id: UUID
    contract_title: str
    current_status: str
    created_at: datetime
    status_changes: List[StatusChangeResponse]
    internal_reviews: List[ReviewHistoryResponse]
    signature_requests: List[SignatureHistoryResponse]


@router.get("/{contract_draft_id}", response_model=AuditTrailResponse)
async def get_contract_audit_trail(
    contract_draft_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete audit trail for a contract draft.
    Shows all status changes, reviews, and signatures.
    """
    # Get contract draft
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # TODO: Add authorization check - verify user has access to this deal

    # Get status changes
    status_changes = db.query(ContractStatusHistory).filter(
        ContractStatusHistory.contract_draft_id == contract_draft_id
    ).order_by(ContractStatusHistory.changed_at.desc()).all()

    status_change_responses = [
        StatusChangeResponse(
            id=change.id,
            old_status=change.old_status,
            new_status=change.new_status,
            changed_by_name=change.changed_by.full_name,
            changed_by_email=change.changed_by.email,
            reason=change.reason,
            changed_at=change.changed_at,
            ip_address=change.ip_address
        )
        for change in status_changes
    ]

    # Get internal reviews
    reviews = db.query(InternalReview).filter(
        InternalReview.contract_draft_id == contract_draft_id
    ).order_by(InternalReview.reviewed_at.desc()).all()

    review_responses = [
        ReviewHistoryResponse(
            id=review.id,
            reviewer_name=review.reviewer.full_name,
            reviewer_email=review.reviewer.email,
            action=review.action.value,
            comments=review.comments,
            draft_version=review.draft_version,
            reviewed_at=review.reviewed_at,
            ip_address=review.ip_address
        )
        for review in reviews
    ]

    # Get signature requests
    signatures = db.query(SignatureRequest).filter(
        SignatureRequest.contract_draft_id == contract_draft_id
    ).order_by(SignatureRequest.requested_at.desc()).all()

    signature_responses = [
        SignatureHistoryResponse(
            id=sig.id,
            signer_name=sig.signer_name,
            signer_email=sig.signer_email,
            signer_role=sig.signer_role.value,
            status=sig.status.value,
            requested_at=sig.requested_at,
            signed_at=sig.signed_at,
            declined_at=sig.declined_at
        )
        for sig in signatures
    ]

    return AuditTrailResponse(
        contract_id=draft.id,
        contract_title=draft.title,
        current_status=draft.status.value,
        created_at=draft.created_at,
        status_changes=status_change_responses,
        internal_reviews=review_responses,
        signature_requests=signature_responses
    )


@router.post("/{contract_draft_id}/log-status-change")
async def log_status_change(
    contract_draft_id: UUID,
    old_status: str | None,
    new_status: str,
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually log a status change (used by other endpoints).
    This should typically be called automatically when status changes.
    """
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    history_entry = ContractStatusHistory(
        contract_draft_id=contract_draft_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=current_user.id,
        reason=reason
    )

    db.add(history_entry)
    db.commit()

    return {"message": "Status change logged", "id": str(history_entry.id)}
