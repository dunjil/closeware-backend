"""
Usage tracking service for subscription billing.
Records deal usage and calculates overages.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import (
    Subscription, UsageRecord, UsageType,
    Organization, Deal, ContractDraft, User
)


class UsageService:
    """Handles usage tracking for subscription billing"""

    @staticmethod
    def record_contract_generation(
        db: Session,
        organization_id: UUID,
        deal_id: UUID,
        contract_draft_id: UUID,
        user_id: UUID,
        description: str = None
    ) -> UsageRecord:
        """
        Record a contract generation event (counts as 1 deal usage).

        Only the FIRST generation for a deal counts.
        Regenerations/revisions don't count as additional deals.
        """
        # Check if we've already recorded usage for this deal
        existing = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.organization_id == organization_id,
                UsageRecord.deal_id == deal_id,
                UsageRecord.usage_type == UsageType.CONTRACT_GENERATION
            )
            .first()
        )

        if existing:
            # Already counted this deal, don't charge again
            return existing

        # Get organization's subscription
        subscription = (
            db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .first()
        )

        if not subscription:
            raise ValueError(f"No subscription found for organization {organization_id}")

        if not subscription.is_active():
            raise ValueError(f"Subscription is not active (status: {subscription.status.value})")

        # Create usage record
        usage = UsageRecord(
            subscription_id=subscription.id,
            organization_id=organization_id,
            usage_type=UsageType.CONTRACT_GENERATION,
            deal_id=deal_id,
            contract_draft_id=contract_draft_id,
            user_id=user_id,
            description=description or f"Contract generation for deal",
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end
        )

        db.add(usage)
        db.commit()
        db.refresh(usage)

        return usage

    @staticmethod
    def get_usage_summary(db: Session, subscription_id: UUID) -> dict:
        """
        Get usage summary for a subscription's current billing period.

        Returns:
        {
            "included_deals": 2,
            "deals_used": 5,
            "overage_deals": 3,
            "base_price": 150000,
            "overage_price": 50000,
            "overage_cost": 150000,
            "total_cost": 300000,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30"
        }
        """
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        deals_used = subscription.deals_used_this_period(db)
        overage_deals = subscription.overage_deals_this_period(db)
        overage_cost = overage_deals * float(subscription.overage_price)
        total_cost = float(subscription.base_price) + overage_cost

        return {
            "included_deals": subscription.included_deals,
            "deals_used": deals_used,
            "overage_deals": overage_deals,
            "base_price": float(subscription.base_price),
            "overage_price": float(subscription.overage_price),
            "overage_cost": overage_cost,
            "total_cost": total_cost,
            "period_start": subscription.current_period_start.isoformat(),
            "period_end": subscription.current_period_end.isoformat(),
            "tier": subscription.tier.value,
            "status": subscription.status.value
        }

    @staticmethod
    def can_use_feature(db: Session, organization_id: UUID) -> tuple[bool, str]:
        """
        Check if organization can use a feature (has active subscription).

        Returns: (can_use, reason_if_not)
        """
        subscription = (
            db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .first()
        )

        if not subscription:
            return False, "No active subscription. Please subscribe to continue."

        if not subscription.is_active():
            return False, f"Subscription is {subscription.status.value}. Please renew to continue."

        # Check if trial has expired
        if subscription.is_trial() and subscription.trial_ends_at and datetime.utcnow() > subscription.trial_ends_at:
            return False, "Trial period has ended. Please upgrade to a paid plan."

        return True, ""

    @staticmethod
    def get_usage_breakdown(db: Session, subscription_id: UUID, limit: int = 50):
        """Get detailed usage records for current billing period"""
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            return []

        records = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.subscription_id == subscription_id,
                UsageRecord.created_at >= subscription.current_period_start,
                UsageRecord.created_at <= subscription.current_period_end
            )
            .order_by(UsageRecord.created_at.desc())
            .limit(limit)
            .all()
        )

        # Enrich with deal/user info
        result = []
        for record in records:
            deal = db.query(Deal).filter(Deal.id == record.deal_id).first() if record.deal_id else None
            user = db.query(User).filter(User.id == record.user_id).first() if record.user_id else None

            result.append({
                "id": str(record.id),
                "usage_type": record.usage_type.value,
                "description": record.description,
                "deal_title": deal.title if deal else None,
                "user_name": user.full_name if user else None,
                "created_at": record.created_at.isoformat()
            })

        return result


# Singleton instance
usage_service = UsageService()
