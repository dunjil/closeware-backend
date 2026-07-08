"""
Subscription usage endpoints - track deal usage and enforce limits
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionTier
from app.api.deps import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class UsageResponse(BaseModel):
    tier: str
    billing_period: str
    deal_limit: Optional[int]  # None = unlimited
    deals_used: int
    deals_remaining: Optional[int]  # None = unlimited
    can_create_deal: bool
    should_upgrade: bool  # True if at 80%+ of limit
    period_start: str
    period_end: str


class UpgradeRecommendation(BaseModel):
    current_tier: str
    recommended_tier: str
    reason: str
    monthly_price: float
    yearly_price: float


@router.get("/usage", response_model=UsageResponse)
def get_subscription_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription usage for the user's organization.
    Shows deals used, remaining, and whether they can create more deals.
    """
    # Get organization's subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Get usage stats
    deals_used = subscription.deals_used_this_period(db)
    can_create = subscription.can_create_deal(db)

    # Calculate remaining deals
    if subscription.deal_limit is None:
        # Unlimited (Enterprise)
        deals_remaining = None
        should_upgrade = False
    else:
        deals_remaining = subscription.deals_remaining_this_period(db)
        # Suggest upgrade if at 80% or more of limit
        usage_percentage = (deals_used / subscription.deal_limit) * 100 if subscription.deal_limit > 0 else 0
        should_upgrade = usage_percentage >= 80

    return UsageResponse(
        tier=subscription.tier.value,
        billing_period=subscription.billing_period.value,
        deal_limit=subscription.deal_limit,
        deals_used=deals_used,
        deals_remaining=deals_remaining,
        can_create_deal=can_create,
        should_upgrade=should_upgrade,
        period_start=subscription.current_period_start.isoformat(),
        period_end=subscription.current_period_end.isoformat()
    )


@router.get("/upgrade-recommendation", response_model=UpgradeRecommendation)
def get_upgrade_recommendation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recommended upgrade tier based on current usage and tier.
    """
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == current_user.organization_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Determine recommended tier
    current_tier = subscription.tier
    deals_used = subscription.deals_used_this_period(db)

    if current_tier == SubscriptionTier.FREE:
        recommended_tier = SubscriptionTier.PRO
        reason = f"You've used {deals_used}/2 deals. Upgrade to Pro for 20 deals/month."
        monthly_price = 99
        yearly_price = 950
    elif current_tier == SubscriptionTier.PRO:
        recommended_tier = SubscriptionTier.TEAM
        reason = f"You've used {deals_used}/20 deals. Upgrade to Team for 100 deals/month and team collaboration."
        monthly_price = 299
        yearly_price = 2850
    elif current_tier == SubscriptionTier.TEAM:
        recommended_tier = SubscriptionTier.ENTERPRISE
        reason = f"You've used {deals_used}/100 deals. Upgrade to Enterprise for unlimited deals."
        monthly_price = None
        yearly_price = None
    else:
        # Already on Enterprise
        raise HTTPException(status_code=200, detail="Already on highest tier")

    return UpgradeRecommendation(
        current_tier=current_tier.value,
        recommended_tier=recommended_tier.value,
        reason=reason,
        monthly_price=monthly_price,
        yearly_price=yearly_price
    )
