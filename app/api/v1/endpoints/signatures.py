from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.models.signature import Signature
from app.models.contract_draft import ContractDraft
from app.api.dependencies import get_current_user

router = APIRouter()


class SignatureCreate(BaseModel):
    signer_name: str
    signer_title: str
    signer_email: Optional[str] = None
    signature_data: str  # SVG path or base64
    signature_type: str = "drawn"
    is_buyer: bool = True


class SignatureResponse(BaseModel):
    id: str
    contract_draft_id: str
    signer_name: str
    signer_title: str
    signer_email: Optional[str]
    signature_type: str
    signed_at: datetime
    is_buyer: bool

    class Config:
        from_attributes = True


@router.post("/{contract_draft_id}", response_model=SignatureResponse)
async def sign_contract(
    contract_draft_id: str,
    signature_data: SignatureCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Sign a contract draft"""
    # Verify contract draft exists
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # Create signature
    signature = Signature(
        contract_draft_id=contract_draft_id,
        signer_name=signature_data.signer_name,
        signer_title=signature_data.signer_title,
        signer_email=signature_data.signer_email,
        signature_data=signature_data.signature_data,
        signature_type=signature_data.signature_type,
        is_buyer=signature_data.is_buyer,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        signed_at=datetime.utcnow(),
    )

    db.add(signature)
    db.commit()
    db.refresh(signature)

    return signature


@router.get("/{contract_draft_id}", response_model=List[SignatureResponse])
async def get_signatures(
    contract_draft_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all signatures for a contract draft"""
    signatures = db.query(Signature).filter(
        Signature.contract_draft_id == contract_draft_id
    ).all()

    return signatures


@router.delete("/{signature_id}")
async def delete_signature(
    signature_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a signature"""
    signature = db.query(Signature).filter(Signature.id == signature_id).first()
    if not signature:
        raise HTTPException(status_code=404, detail="Signature not found")

    db.delete(signature)
    db.commit()

    return {"message": "Signature deleted successfully"}
