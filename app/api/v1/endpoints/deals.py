from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db.base import get_db
from app.schemas.deal import DealCreate, DealUpdate, DealResponse
from app.models.deal import Deal

router = APIRouter()


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    deal_data: DealCreate,
    organization_id: UUID,
    creator_id: UUID,
    db: Session = Depends(get_db)
):
    from app.core.validation import sanitize_string
    from app.models.user import User
    from app.models.organization import Organization

    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Validate creator exists and belongs to organization
    creator = db.query(User).filter(User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")
    if creator.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator does not belong to this organization")

    # Validate and sanitize title
    title = sanitize_string(deal_data.title, max_length=200)
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deal title is required")

    # Validate price if provided
    if deal_data.agreed_price is not None and deal_data.agreed_price < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price cannot be negative")

    new_deal = Deal(
        organization_id=organization_id,
        creator_id=creator_id,
        deal_type=deal_data.deal_type,
        title=title,
        asset_description=sanitize_string(deal_data.asset_description, max_length=5000),
        agreed_price=deal_data.agreed_price,
        currency=deal_data.currency,
        parties=deal_data.parties,
        terms=deal_data.terms
    )
    db.add(new_deal)
    db.commit()
    db.refresh(new_deal)

    return DealResponse(
        **new_deal.__dict__,
        correspondence_count=0,
        documents_count=0,
        latest_draft_version=None
    )


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: UUID, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    correspondence_count = len(deal.correspondence)
    documents_count = len(deal.documents)
    latest_draft_version = max([d.version for d in deal.contract_drafts], default=None)

    return DealResponse(
        **deal.__dict__,
        correspondence_count=correspondence_count,
        documents_count=documents_count,
        latest_draft_version=latest_draft_version
    )


@router.get("/", response_model=List[DealResponse])
async def list_deals(organization_id: UUID, db: Session = Depends(get_db)):
    deals = db.query(Deal).filter(Deal.organization_id == organization_id).all()

    result = []
    for deal in deals:
        result.append(DealResponse(
            **deal.__dict__,
            correspondence_count=len(deal.correspondence),
            documents_count=len(deal.documents),
            latest_draft_version=max([d.version for d in deal.contract_drafts], default=None)
        ))

    return result


@router.patch("/{deal_id}", response_model=DealResponse)
async def update_deal(deal_id: UUID, deal_update: DealUpdate, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    for field, value in deal_update.dict(exclude_unset=True).items():
        setattr(deal, field, value)

    db.commit()
    db.refresh(deal)

    return DealResponse(
        **deal.__dict__,
        correspondence_count=len(deal.correspondence),
        documents_count=len(deal.documents),
        latest_draft_version=max([d.version for d in deal.contract_drafts], default=None)
    )
