from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
from app.db.base import Base


class SubscriptionTier(str, enum.Enum):
    FREE = "free"  # $0/month, 2 deals/month
    PRO = "pro"  # $99/month or $950/year, 20 deals/month
    TEAM = "team"  # $299/month or $2,850/year, 100 deals/month
    ENTERPRISE = "enterprise"  # Custom pricing, unlimited deals


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"  # Free trial period
    ACTIVE = "active"  # Paid and current
    PAST_DUE = "past_due"  # Payment failed but still accessible
    CANCELLED = "cancelled"  # User cancelled
    EXPIRED = "expired"  # Not renewed


class BillingPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Subscription(Base):
    """
    Organization subscription to Closeware.
    Tracks tier, billing period, included deals, and status.
    """
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Subscription details
    tier = Column(Enum(SubscriptionTier), nullable=False, default=SubscriptionTier.FREE)
    billing_period = Column(Enum(BillingPeriod), nullable=False, default=BillingPeriod.MONTHLY)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.TRIAL)

    # Pricing
    currency = Column(String(3), nullable=False, default="USD")
    base_price = Column(Numeric(precision=12, scale=2), nullable=False)  # Monthly/annual subscription price
    deal_limit = Column(Integer, nullable=True)  # Max deals per period (None = unlimited for Enterprise)

    # Billing cycle dates
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_ends_at = Column(DateTime, nullable=True)

    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="subscription")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]

    def is_trial(self) -> bool:
        """Check if in trial period"""
        return self.status == SubscriptionStatus.TRIAL and self.trial_ends_at and datetime.utcnow() < self.trial_ends_at

    def deals_used_this_period(self, db) -> int:
        """Count deals used in current billing period"""
        from app.models.usage_record import UsageRecord
        count = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.subscription_id == self.id,
                UsageRecord.created_at >= self.current_period_start,
                UsageRecord.created_at <= self.current_period_end
            )
            .count()
        )
        return count

    def can_create_deal(self, db) -> bool:
        """Check if organization can create another deal this period"""
        # Enterprise has unlimited deals
        if self.tier == SubscriptionTier.ENTERPRISE:
            return True

        # Free tier during trial
        if self.tier == SubscriptionTier.FREE and self.is_trial():
            return True

        # Check against limit
        if self.deal_limit is None:
            return True

        used = self.deals_used_this_period(db)
        return used < self.deal_limit

    def deals_remaining_this_period(self, db) -> int:
        """Get number of deals remaining in current period"""
        if self.deal_limit is None:  # Unlimited (Enterprise)
            return float('inf')

        used = self.deals_used_this_period(db)
        remaining = max(0, self.deal_limit - used)
        return remaining

    @staticmethod
    def get_tier_pricing(tier: SubscriptionTier, billing_period: BillingPeriod = BillingPeriod.MONTHLY, currency: str = "USD"):
        """
        Get pricing details for a subscription tier.
        Simple monthly/yearly pricing with hard limits (no overage charges).
        """
        # Base pricing in USD
        base_pricing_usd = {
            SubscriptionTier.FREE: {
                BillingPeriod.MONTHLY: {
                    "base_price": 0,
                    "deal_limit": 2,  # 2 deals per month
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 0,
                    "deal_limit": 24,  # 24 deals per year (2/month)
                }
            },
            SubscriptionTier.PRO: {
                BillingPeriod.MONTHLY: {
                    "base_price": 99,
                    "deal_limit": 20,  # 20 deals per month
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 950,  # ~20% discount ($99 * 12 = $1,188)
                    "deal_limit": 240,  # 240 deals per year (20/month)
                }
            },
            SubscriptionTier.TEAM: {
                BillingPeriod.MONTHLY: {
                    "base_price": 299,
                    "deal_limit": 100,  # 100 deals per month
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 2850,  # ~20% discount ($299 * 12 = $3,588)
                    "deal_limit": 1200,  # 1200 deals per year (100/month)
                }
            },
            SubscriptionTier.ENTERPRISE: {
                BillingPeriod.MONTHLY: {
                    "base_price": None,  # Custom pricing
                    "deal_limit": None,  # Unlimited
                },
                BillingPeriod.ANNUAL: {
                    "base_price": None,  # Custom pricing
                    "deal_limit": None,  # Unlimited
                }
            }
        }

        # Get pricing in USD (no currency conversion for now - keep it simple)
        pricing = base_pricing_usd[tier][billing_period]

        return {
            "base_price": pricing["base_price"],
            "deal_limit": pricing["deal_limit"],
            "currency": "USD"
        }
