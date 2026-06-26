from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
from app.db.base import Base


class SubscriptionTier(str, enum.Enum):
    LITE = "lite"  # ₦75K/month, 1 deal included, ₦60K per extra
    PRO = "pro"  # ₦150K/month, 2 deals included, ₦50K per extra
    ENTERPRISE = "enterprise"  # ₦500K/month, 10 deals included, ₦40K per extra


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
    tier = Column(Enum(SubscriptionTier), nullable=False, default=SubscriptionTier.PRO)
    billing_period = Column(Enum(BillingPeriod), nullable=False, default=BillingPeriod.MONTHLY)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.TRIAL)

    # Pricing (in NGN - Naira)
    base_price = Column(Numeric(precision=12, scale=2), nullable=False)  # Monthly/annual base price
    included_deals = Column(Integer, nullable=False)  # Deals included in base price
    overage_price = Column(Numeric(precision=12, scale=2), nullable=False)  # Price per additional deal

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

    def overage_deals_this_period(self, db) -> int:
        """Calculate how many deals exceed the included amount"""
        used = self.deals_used_this_period(db)
        overage = max(0, used - self.included_deals)
        return overage

    def calculate_period_cost(self, db) -> float:
        """Calculate total cost for current period (base + overages)"""
        overage_count = self.overage_deals_this_period(db)
        overage_cost = overage_count * float(self.overage_price)
        total = float(self.base_price) + overage_cost
        return total

    @staticmethod
    def get_tier_pricing(tier: SubscriptionTier, billing_period: BillingPeriod = BillingPeriod.MONTHLY):
        """Get pricing details for a subscription tier"""
        pricing = {
            SubscriptionTier.LITE: {
                BillingPeriod.MONTHLY: {
                    "base_price": 75000,
                    "included_deals": 1,
                    "overage_price": 60000
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 750000,  # 10 months price (2 months free)
                    "included_deals": 12,
                    "overage_price": 60000
                }
            },
            SubscriptionTier.PRO: {
                BillingPeriod.MONTHLY: {
                    "base_price": 150000,
                    "included_deals": 2,
                    "overage_price": 50000
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 1500000,  # 10 months price (2 months free)
                    "included_deals": 24,
                    "overage_price": 50000
                }
            },
            SubscriptionTier.ENTERPRISE: {
                BillingPeriod.MONTHLY: {
                    "base_price": 500000,
                    "included_deals": 10,
                    "overage_price": 40000
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 5000000,  # 10 months price
                    "included_deals": 120,
                    "overage_price": 40000
                }
            }
        }
        return pricing[tier][billing_period]
