from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.db.base import get_db
from app.models.deal import Deal
from app.models.correspondence import Correspondence
from app.models.organization import Organization
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.offer_letter_generator import offer_letter_generator

router = APIRouter()


class GenerateOfferLetterRequest(BaseModel):
    letter_type: str = "offer"  # "offer" or "counter_offer"
    proposed_price: Optional[float] = None
    proposed_terms: Optional[str] = None
    additional_notes: Optional[str] = None


class GenerateNDARequestRequest(BaseModel):
    counterparty_name: str
    evaluation_purpose: str


class OfferLetterResponse(BaseModel):
    letter_content: str
    deal_id: UUID
    letter_type: str


@router.post("/{deal_id}/generate-offer-letter", response_model=OfferLetterResponse)
async def generate_offer_letter(
    deal_id: UUID,
    request: GenerateOfferLetterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a professional offer or counter-offer letter using AI.
    Letter is generated but NOT automatically saved - user must review first.
    """
    # Get deal
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Get organization
    organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # TODO: Add authorization check - verify user has access to this deal

    try:
        # Generate letter using AI
        letter_content = offer_letter_generator.generate_offer_letter(
            deal=deal,
            organization=organization,
            letter_type=request.letter_type,
            proposed_price=request.proposed_price,
            proposed_terms=request.proposed_terms,
            additional_notes=request.additional_notes
        )

        return OfferLetterResponse(
            letter_content=letter_content,
            deal_id=deal.id,
            letter_type=request.letter_type
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate letter: {str(e)}")


@router.post("/{deal_id}/generate-nda-request", response_model=OfferLetterResponse)
async def generate_nda_request_letter(
    deal_id: UUID,
    request: GenerateNDARequestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a professional letter requesting NDA execution.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        letter_content = offer_letter_generator.generate_nda_request_letter(
            deal=deal,
            organization=organization,
            counterparty_name=request.counterparty_name,
            evaluation_purpose=request.evaluation_purpose
        )

        return OfferLetterResponse(
            letter_content=letter_content,
            deal_id=deal.id,
            letter_type="nda_request"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate NDA request: {str(e)}")


@router.post("/{deal_id}/save-offer-letter")
async def save_offer_letter(
    deal_id: UUID,
    letter_content: str,
    letter_type: str,
    subject: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save a reviewed and approved offer letter as correspondence.
    This is called after user reviews the AI-generated letter.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Create correspondence entry
    correspondence = Correspondence(
        deal_id=deal.id,
        correspondence_type="offer" if letter_type == "offer" else "counter_offer",
        subject=subject,
        content=letter_content,
        sender=current_user.organization.name if current_user.organization else current_user.full_name,
        recipient=deal.seller_name or "Counterparty",
        is_outgoing=True
    )

    db.add(correspondence)
    db.commit()
    db.refresh(correspondence)

    return {
        "message": "Offer letter saved successfully",
        "correspondence_id": str(correspondence.id)
    }
