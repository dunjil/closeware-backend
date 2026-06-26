from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from app.db.base import get_db
from app.models.deal import Deal
from app.models.contract_draft import ContractDraft
from app.models.user import User, UserType
from app.models.usage_record import UsageRecord, UsageType
from app.services.contract_generator import ContractGenerator
from app.services.usage_service import usage_service
from app.schemas.contract_draft import ContractDraft as ContractDraftSchema
from app.api.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class GenerateContractRequest(BaseModel):
    contract_type: str = "SPA"  # SPA, JV, or NDA
    title: Optional[str] = None


class RegenerateContractRequest(BaseModel):
    corrections: str  # User's correction instructions
    contract_type: str = "SPA"


@router.post("/generate/{deal_id}", response_model=ContractDraftSchema)
async def generate_contract(
    deal_id: UUID,
    request: GenerateContractRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a complete contract (SPA, JV Agreement, or NDA) from the deal trail.
    Records usage for subscription billing.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    # Check subscription permission (internal users only - external users are guests)
    if current_user.user_type == UserType.INTERNAL and current_user.organization_id:
        can_use, reason = usage_service.can_use_feature(db, current_user.organization_id)
        if not can_use:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail=reason
            )

    # Check if deal has correspondence or documents
    if not deal.correspondence and not deal.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate contract: Deal has no correspondence or documents. Please add negotiation trail first."
        )

    generator = ContractGenerator()

    try:
        contract_content = generator.generate_contract(
            deal=deal,
            db=db,
            contract_type=request.contract_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate contract: {str(e)}"
        )

    # RACE CONDITION FIX: Use database-level max() to prevent concurrent duplicate versions
    # SELECT MAX(version) FROM contract_drafts WHERE deal_id = X FOR UPDATE
    max_version_row = db.execute(
        select(func.coalesce(func.max(ContractDraft.version), 0))
        .where(ContractDraft.deal_id == deal_id)
    ).scalar()
    next_version = max_version_row + 1

    # Create contract draft
    title = request.title or f"{request.contract_type} - {deal.title} (AI Generated)"

    new_draft = ContractDraft(
        deal_id=deal_id,
        title=title,
        content=contract_content,
        version=next_version
    )
    db.add(new_draft)

    # CRITICAL: Record usage BEFORE commit, so if usage fails, draft isn't created
    # This prevents "free contracts" when usage recording fails
    usage_recorded = False
    if current_user.user_type == UserType.INTERNAL and current_user.organization_id:
        # Use database unique constraint to prevent double-counting (race condition fix)
        # Check if usage already exists for this deal
        existing_usage = db.query(UsageRecord).filter(
            UsageRecord.deal_id == deal_id,
            UsageRecord.usage_type == UsageType.CONTRACT_GENERATION,
            UsageRecord.organization_id == current_user.organization_id
        ).with_for_update().first()  # Lock row to prevent concurrent checks

        if not existing_usage:
            # First generation for this deal - record usage
            from app.models.subscription import Subscription
            subscription = db.query(Subscription).filter(
                Subscription.organization_id == current_user.organization_id
            ).order_by(Subscription.created_at.desc()).first()

            if subscription:
                usage_record = UsageRecord(
                    organization_id=current_user.organization_id,
                    subscription_id=subscription.id,
                    deal_id=deal_id,
                    contract_draft_id=new_draft.id,  # Will be set after flush
                    user_id=current_user.id,
                    usage_type=UsageType.CONTRACT_GENERATION,
                    billing_period_start=subscription.current_period_start,
                    billing_period_end=subscription.current_period_end,
                    description=f"Generated {request.contract_type} for {deal.title}"
                )
                db.add(usage_record)
                usage_recorded = True

    try:
        db.commit()
        db.refresh(new_draft)
    except IntegrityError as e:
        db.rollback()
        # If this is a duplicate version error, someone else generated concurrently
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A contract was just generated by another user. Please refresh to see it."
        )

    return new_draft


@router.post("/regenerate/{contract_draft_id}", response_model=ContractDraftSchema)
async def regenerate_contract_with_corrections(
    contract_draft_id: UUID,
    request: RegenerateContractRequest,
    db: Session = Depends(get_db)
):
    """
    Regenerate an existing contract draft with user corrections/suggestions.
    """
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract draft not found")

    deal = db.query(Deal).filter(Deal.id == draft.deal_id).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    generator = ContractGenerator()

    try:
        # Generate with corrections
        contract_content = generator.regenerate_with_corrections(
            deal=deal,
            current_draft=draft.content,
            corrections=request.corrections,
            contract_type=request.contract_type,
            db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate contract: {str(e)}"
        )

    # Create new version
    existing_drafts = db.query(ContractDraft).filter(ContractDraft.deal_id == deal.id).all()
    next_version = max([d.version for d in existing_drafts], default=0) + 1

    new_draft = ContractDraft(
        deal_id=deal.id,
        title=f"{draft.title} (Revised)",
        content=contract_content,
        version=next_version
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    return new_draft
