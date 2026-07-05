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
from app.utils.status_logger import update_status_with_logging

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
    # Validate signers list is not empty
    if not request.signers or len(request.signers) == 0:
        raise HTTPException(status_code=400, detail="At least one signer is required")

    # Get contract draft
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # Validate contract status (must be draft or reviewed to mark ready for signing)
    if draft.status not in [DraftStatus.DRAFT, DraftStatus.REVIEWED]:
        raise HTTPException(
            status_code=400,
            detail=f"Contract must be in draft or reviewed status to mark ready for signing. Current status: {draft.status.value}"
        )

    # TODO: Add authorization check - verify current_user has access to the deal
    # This requires loading draft.deal and checking organization membership

    # Check for duplicate signature requests (same email on same contract)
    existing_requests = db.query(SignatureRequest).filter(
        SignatureRequest.contract_draft_id == contract_draft_id,
        SignatureRequest.status == SignatureRequestStatus.PENDING
    ).all()
    existing_emails = {req.signer_email for req in existing_requests}

    for signer_data in request.signers:
        if signer_data.signer_email in existing_emails:
            raise HTTPException(
                status_code=400,
                detail=f"Signature request already exists for {signer_data.signer_email}"
            )

    # Update status and log the change
    update_status_with_logging(
        db=db,
        contract_draft=draft,
        new_status=DraftStatus.AWAITING_SIGNATURES,
        changed_by=current_user,
        reason=f"Signature requests sent to {len(request.signers)} signers"
    )

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
        db.flush()  # Get the request ID and access_token
        signature_requests.append(sig_request)

        # Send email notification
        try:
            email_service.send_signature_request(
                signer_email=signer_data.signer_email,
                signer_name=signer_data.signer_name,
                contract_title=draft.title,
                request_id=str(sig_request.id),
                access_token=sig_request.access_token,
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
    token: str,  # Access token for security
    db: Session = Depends(get_db)
):
    """
    Fulfill a signature request by signing.
    Requires valid access token sent in the signature request email.
    """
    # Get signature request
    sig_request = db.query(SignatureRequest).filter(SignatureRequest.id == request_id).first()
    if not sig_request:
        raise HTTPException(status_code=404, detail="Signature request not found")

    # Validate access token
    if sig_request.access_token != token:
        raise HTTPException(status_code=403, detail="Invalid access token")

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

    # Get contract owner for logging (use requester of signatures)
    first_request = all_requests[0]
    contract_owner = first_request.requested_by

    if all_signed:
        # Update status and log the change
        update_status_with_logging(
            db=db,
            contract_draft=draft,
            new_status=DraftStatus.FULLY_EXECUTED,
            changed_by=contract_owner,  # Log as contract owner
            reason=f"All {len(all_requests)} signatures collected"
        )

        # Send notification to contract owner
        try:
            email_service.send_contract_fully_executed_notification(
                owner_email=contract_owner.email,
                owner_name=contract_owner.full_name,
                contract_title=draft.title,
                contract_draft_id=str(draft.id),
                deal_name=draft.deal.asset_description if draft.deal.asset_description else "Deal"
            )
        except Exception as e:
            print(f"Failed to send fully executed notification: {str(e)}")
            # Don't fail the request if email fails
    else:
        # Update status and log the change
        signed_count = sum(1 for req in all_requests if req.status == SignatureRequestStatus.SIGNED)
        update_status_with_logging(
            db=db,
            contract_draft=draft,
            new_status=DraftStatus.PARTIALLY_SIGNED,
            changed_by=contract_owner,
            reason=f"{signed_count} of {len(all_requests)} signatures collected"
        )

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
