from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from uuid import UUID

from app.db.base import get_db
from app.models.signature_request import SignatureRequest, SignatureRole, SignatureRequestStatus
from app.models.contract_draft import ContractDraft, DraftStatus
from app.models.signature import Signature
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.email_service import email_service

router = APIRouter()


class SignatureRequestCreate(BaseModel):
    signer_name: str
    signer_email: EmailStr
    signer_title: str | None = None
    signer_role: SignatureRole
    request_message: str | None = None
    expires_in_days: int = 30


class SignatureRequestResponse(BaseModel):
    id: UUID
    contract_draft_id: UUID
    signer_name: str
    signer_email: str
    signer_title: str | None
    signer_role: SignatureRole
    status: SignatureRequestStatus
    requested_at: datetime
    expires_at: datetime | None
    signed_at: datetime | None

    class Config:
        from_attributes = True


class MarkReadyForSigningRequest(BaseModel):
    signers: List[SignatureRequestCreate]


class SignContractRequest(BaseModel):
    signature_data: str
    signature_type: str = "drawn"


@router.post("/{contract_draft_id}/mark-ready")
async def mark_contract_ready_for_signing(
    contract_draft_id: UUID,
    request: MarkReadyForSigningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark contract as ready for signing and send signature requests.
    """
    # Get contract draft
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # Update status
    draft.status = DraftStatus.AWAITING_SIGNATURES

    # Create signature requests
    signature_requests = []
    for signer_data in request.signers:
        expires_at = datetime.utcnow() + timedelta(days=signer_data.expires_in_days)

        sig_request = SignatureRequest(
            contract_draft_id=contract_draft_id,
            signer_name=signer_data.signer_name,
            signer_email=signer_data.signer_email,
            signer_title=signer_data.signer_title,
            signer_role=signer_data.signer_role,
            request_message=signer_data.request_message,
            requested_by_id=current_user.id,
            expires_at=expires_at
        )

        db.add(sig_request)
        signature_requests.append(sig_request)

        # Send email notification
        try:
            email_service.send_signature_request(
                signer_email=signer_data.signer_email,
                signer_name=signer_data.signer_name,
                contract_title=draft.title,
                contract_draft_id=str(contract_draft_id),
                requested_by=current_user.full_name,
                message=signer_data.request_message,
                expires_at=expires_at
            )
        except Exception as e:
            print(f"Failed to send signature request email: {str(e)}")

    db.commit()

    return {
        "message": f"Contract marked ready for signing. {len(signature_requests)} signature requests sent.",
        "signature_requests": len(signature_requests),
        "status": draft.status.value
    }


@router.get("/{contract_draft_id}", response_model=List[SignatureRequestResponse])
async def get_signature_requests(
    contract_draft_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all signature requests for a contract draft"""
    requests = db.query(SignatureRequest).filter(
        SignatureRequest.contract_draft_id == contract_draft_id
    ).all()

    return requests


@router.post("/{request_id}/sign")
async def fulfill_signature_request(
    request_id: UUID,
    sign_request: SignContractRequest,
    db: Session = Depends(get_db)
):
    """
    Fulfill a signature request by signing.
    """
    # Get signature request
    sig_request = db.query(SignatureRequest).filter(SignatureRequest.id == request_id).first()
    if not sig_request:
        raise HTTPException(status_code=404, detail="Signature request not found")

    # Check if expired
    if sig_request.expires_at and datetime.utcnow() > sig_request.expires_at:
        sig_request.status = SignatureRequestStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Signature request has expired")

    # Check if already signed
    if sig_request.status == SignatureRequestStatus.SIGNED:
        raise HTTPException(status_code=400, detail="Already signed")

    # Create signature
    signature = Signature(
        contract_draft_id=sig_request.contract_draft_id,
        signer_name=sig_request.signer_name,
        signer_email=sig_request.signer_email,
        signer_title=sig_request.signer_title,
        signature_data=sign_request.signature_data,
        signature_type=sign_request.signature_type,
        is_buyer=(sig_request.signer_role == SignatureRole.BUYER)
    )

    db.add(signature)
    db.flush()  # Get signature ID

    # Mark request as signed
    sig_request.mark_signed(signature.id)

    # Check if all requests are now signed
    draft = sig_request.contract_draft
    all_requests = db.query(SignatureRequest).filter(
        SignatureRequest.contract_draft_id == draft.id
    ).all()

    all_signed = all([req.status == SignatureRequestStatus.SIGNED for req in all_requests])

    if all_signed:
        draft.status = DraftStatus.FULLY_EXECUTED
    else:
        draft.status = DraftStatus.PARTIALLY_SIGNED

    db.commit()

    return {
        "message": "Signature recorded successfully",
        "contract_status": draft.status.value,
        "all_signed": all_signed
    }


@router.post("/{request_id}/decline")
async def decline_signature_request(
    request_id: UUID,
    reason: str | None = None,
    db: Session = Depends(get_db)
):
    """Decline a signature request"""
    sig_request = db.query(SignatureRequest).filter(SignatureRequest.id == request_id).first()
    if not sig_request:
        raise HTTPException(status_code=404, detail="Signature request not found")

    sig_request.mark_declined(reason)
    db.commit()

    return {
        "message": "Signature request declined",
        "reason": reason
    }


@router.get("/request/{request_id}", response_model=SignatureRequestResponse)
async def get_signature_request_details(
    request_id: UUID,
    db: Session = Depends(get_db)
):
    """Get details of a specific signature request (for signing page)"""
    sig_request = db.query(SignatureRequest).filter(SignatureRequest.id == request_id).first()
    if not sig_request:
        raise HTTPException(status_code=404, detail="Signature request not found")

    return sig_request
