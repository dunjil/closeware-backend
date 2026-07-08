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
    from app.models.subscription import Subscription

    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check subscription and deal limit
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == organization_id
    ).first()

    if not subscription:
        # Create FREE subscription automatically if missing
        from app.models.subscription import BillingPeriod
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        pricing = Subscription.get_tier_pricing(SubscriptionTier.FREE, BillingPeriod.MONTHLY)

        subscription = Subscription(
            organization_id=organization_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            billing_period=BillingPeriod.MONTHLY,
            currency="USD",
            base_price=pricing["base_price"],
            deal_limit=pricing["deal_limit"],
            current_period_start=now,
            current_period_end=period_end,
            trial_ends_at=None
        )
        db.add(subscription)
        db.flush()

    # Check if can create deal
    can_create = subscription.can_create_deal(db)
    if not can_create:
        deals_used = subscription.deals_used_this_period(db)
        deal_limit = subscription.deal_limit
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "deal_limit_reached",
                "message": f"You've reached your limit of {deal_limit} deals this month. Please upgrade your plan to create more deals.",
                "tier": subscription.tier.value,
                "deals_used": deals_used,
                "deal_limit": deal_limit
            }
        )

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
    db.flush()  # Get deal ID before creating usage record

    # Create usage record to track this deal against subscription
    if subscription:
        from app.models.usage_record import UsageRecord, UsageType

        usage_record = UsageRecord(
            subscription_id=subscription.id,
            organization_id=organization_id,
            user_id=creator_id,
            deal_id=new_deal.id,
            usage_type=UsageType.DEAL_CREATED,
            quantity=1,
            description=f"Deal created: {title}"
        )
        db.add(usage_record)

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
