from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
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
    old_status: Optional[str]
    new_status: str
    changed_by_name: str
    changed_by_email: str
    reason: Optional[str]
    changed_at: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class ReviewHistoryResponse(BaseModel):
    id: UUID
    reviewer_name: str
    reviewer_email: str
    action: str
    comments: Optional[str]
    draft_version: int
    reviewed_at: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class SignatureHistoryResponse(BaseModel):
    id: UUID
    signer_name: str
    signer_email: str
    signer_role: str
    status: str
    requested_at: datetime
    signed_at: Optional[datetime]
    declined_at: Optional[datetime]

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
    old_status: Optional[str],
    new_status: str,
    reason: Optional[str] = None,
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


@router.get("/{contract_draft_id}/export/{format}")
async def export_audit_trail(
    contract_draft_id: UUID,
    format: str,  # "pdf" or "docx"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export complete audit trail as PDF or DOCX for legal/compliance use.
    Format: 'pdf' or 'docx'
    """
    from fastapi.responses import StreamingResponse
    from app.services.audit_export_service import audit_export_service

    # Validate format
    if format not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'docx'")

    # Get contract draft
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # TODO: Add authorization check - verify user has access to this deal

    # Get all audit data
    status_changes = db.query(ContractStatusHistory).filter(
        ContractStatusHistory.contract_draft_id == contract_draft_id
    ).order_by(ContractStatusHistory.changed_at).all()

    reviews = db.query(InternalReview).filter(
        InternalReview.contract_draft_id == contract_draft_id
    ).order_by(InternalReview.reviewed_at).all()

    signatures = db.query(SignatureRequest).filter(
        SignatureRequest.contract_draft_id == contract_draft_id
    ).order_by(SignatureRequest.requested_at).all()

    # Generate export
    if format == "pdf":
        buffer = audit_export_service.export_to_pdf(draft, status_changes, reviews, signatures)
        media_type = "application/pdf"
        filename = f"audit_trail_{draft.title.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    else:  # docx
        buffer = audit_export_service.export_to_docx(draft, status_changes, reviews, signatures)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"audit_trail_{draft.title.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.docx"

    # Return file
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
