from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.db.base import get_db
from app.models import (
    User, Organization, Subscription, Invoice, UsageRecord,
    SubscriptionTier, SubscriptionStatus, BillingPeriod,
    InvoiceStatus, UserType
)
from app.api.dependencies import get_current_user
from app.services.usage_service import usage_service
from pydantic import BaseModel

router = APIRouter()


# Schemas
class SubscriptionCreate(BaseModel):
    tier: str  # "lite", "pro", "enterprise"
    billing_period: str = "monthly"  # "monthly" or "annual"
    start_trial: bool = True


class SubscriptionResponse(BaseModel):
    id: str
    tier: str
    billing_period: str
    status: str
    base_price: float
    included_deals: int
    overage_price: float
    current_period_start: str
    current_period_end: str
    trial_ends_at: Optional[str]
    usage_summary: Optional[dict] = None

    class Config:
        from_attributes = True


class UsageSummaryResponse(BaseModel):
    included_deals: int
    deals_used: int
    overage_deals: int
    base_price: float
    overage_price: float
    overage_cost: float
    total_cost: float
    period_start: str
    period_end: str
    tier: str
    status: str


@router.post("/create", response_model=SubscriptionResponse)
def create_subscription(
    sub_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a subscription for the current user's organization.
    Only internal users (org members) can create subscriptions.
    """
    # Only internal users can create org subscriptions
    if current_user.user_type != UserType.INTERNAL:
        raise HTTPException(
            status_code=403,
            detail="Only organization members can create subscriptions"
        )

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # Check if org already has subscription
    existing = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Organization already has a subscription. Use upgrade endpoint to change tiers."
        )

    # Parse tier
    try:
        tier = SubscriptionTier(sub_data.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {sub_data.tier}")

    try:
        billing_period = BillingPeriod(sub_data.billing_period)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid billing period: {sub_data.billing_period}")

    # Get pricing
    pricing = Subscription.get_tier_pricing(tier, billing_period)

    # Calculate period dates
    now = datetime.utcnow()
    if billing_period == BillingPeriod.MONTHLY:
        period_end = now + timedelta(days=30)
    else:  # ANNUAL
        period_end = now + timedelta(days=365)

    # Create subscription
    subscription = Subscription(
        organization_id=current_user.organization_id,
        tier=tier,
        billing_period=billing_period,
        status=SubscriptionStatus.TRIAL if sub_data.start_trial else SubscriptionStatus.ACTIVE,
        base_price=pricing["base_price"],
        included_deals=pricing["included_deals"],
        overage_price=pricing["overage_price"],
        current_period_start=now,
        current_period_end=period_end,
        trial_ends_at=now + timedelta(days=30) if sub_data.start_trial else None,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return SubscriptionResponse(
        id=str(subscription.id),
        tier=subscription.tier.value,
        billing_period=subscription.billing_period.value,
        status=subscription.status.value,
        base_price=float(subscription.base_price),
        included_deals=subscription.included_deals,
        overage_price=float(subscription.overage_price),
        current_period_start=subscription.current_period_start.isoformat(),
        current_period_end=subscription.current_period_end.isoformat(),
        trial_ends_at=subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
    )


@router.get("/current", response_model=SubscriptionResponse)
def get_current_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current organization's subscription with usage summary"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Only organization members can view subscriptions")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for your organization")

    # Get usage summary
    usage_summary = usage_service.get_usage_summary(db, subscription.id)

    return SubscriptionResponse(
        id=str(subscription.id),
        tier=subscription.tier.value,
        billing_period=subscription.billing_period.value,
        status=subscription.status.value,
        base_price=float(subscription.base_price),
        included_deals=subscription.included_deals,
        overage_price=float(subscription.overage_price),
        current_period_start=subscription.current_period_start.isoformat(),
        current_period_end=subscription.current_period_end.isoformat(),
        trial_ends_at=subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
        usage_summary=usage_summary,
    )


@router.get("/usage", response_model=UsageSummaryResponse)
def get_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage summary for current billing period"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    summary = usage_service.get_usage_summary(db, subscription.id)
    return UsageSummaryResponse(**summary)


@router.get("/usage/breakdown")
def get_usage_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed usage breakdown for current period"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    breakdown = usage_service.get_usage_breakdown(db, subscription.id)
    return {"usage_records": breakdown}


@router.get("/can-use-feature")
def check_feature_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if organization can use features (has active subscription)"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        # External users don't need subscriptions (they're guests)
        return {"allowed": True, "reason": ""}

    can_use, reason = usage_service.can_use_feature(db, current_user.organization_id)
    return {"allowed": can_use, "reason": reason}


@router.post("/upgrade")
def upgrade_subscription(
    new_tier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upgrade subscription tier (Lite → Pro → Enterprise)"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Parse new tier
    try:
        new_tier_enum = SubscriptionTier(new_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {new_tier}")

    # Get new pricing
    pricing = Subscription.get_tier_pricing(new_tier_enum, subscription.billing_period)

    # Update subscription
    subscription.tier = new_tier_enum
    subscription.base_price = pricing["base_price"]
    subscription.included_deals = pricing["included_deals"]
    subscription.overage_price = pricing["overage_price"]

    # If upgrading from trial, activate
    if subscription.status == SubscriptionStatus.TRIAL:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.trial_ends_at = None

    db.commit()

    return {"message": f"Subscription upgraded to {new_tier}", "new_tier": new_tier}


@router.post("/cancel")
def cancel_subscription(
    cancel_immediately: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel subscription (ends at period end by default)"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == current_user.organization_id)
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    if cancel_immediately:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
    else:
        subscription.cancel_at_period_end = True

    db.commit()

    return {
        "message": "Subscription cancelled",
        "ends_at": subscription.current_period_end.isoformat() if not cancel_immediately else "immediately"
    }


@router.get("/invoices")
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all invoices for organization"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    invoices = (
        db.query(Invoice)
        .filter(Invoice.organization_id == current_user.organization_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )

    return {
        "invoices": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "status": inv.status.value,
                "period_start": inv.period_start.isoformat(),
                "period_end": inv.period_end.isoformat(),
                "subtotal": float(inv.subtotal),
                "tax_amount": float(inv.tax_amount),
                "total": float(inv.total),
                "payment_due_date": inv.payment_due_date.isoformat(),
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invoices
        ]
    }


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed invoice"""
    if current_user.user_type != UserType.INTERNAL or not current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "status": invoice.status.value,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "subtotal": float(invoice.subtotal),
        "tax_rate": float(invoice.tax_rate),
        "tax_amount": float(invoice.tax_amount),
        "total": float(invoice.total),
        "line_items": invoice.line_items,
        "payment_due_date": invoice.payment_due_date.isoformat(),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "payment_method": invoice.payment_method,
        "notes": invoice.notes,
        "created_at": invoice.created_at.isoformat(),
    }
