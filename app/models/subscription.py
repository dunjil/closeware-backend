from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
from app.db.base import Base


class SubscriptionTier(str, enum.Enum):
    LITE = "lite"  # $180/month, 1 deal included, $145 per extra
    PRO = "pro"  # $360/month, 2 deals included, $120 per extra
    ENTERPRISE = "enterprise"  # $1,200/month, 10 deals included, $95 per extra


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

    # Pricing (in organization's currency)
    currency = Column(String(3), nullable=False, default="USD")  # ISO 4217 currency code (USD, EUR, GBP, NGN, AED, etc.)
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
    def get_tier_pricing(tier: SubscriptionTier, billing_period: BillingPeriod = BillingPeriod.MONTHLY, currency: str = "USD"):
        """
        Get pricing details for a subscription tier in specified currency.
        Global pricing - supports USD, EUR, GBP, NGN, AED, and more.
        """
        # Base pricing in USD (global standard)
        base_pricing_usd = {
            SubscriptionTier.LITE: {
                BillingPeriod.MONTHLY: {
                    "base_price": 180,
                    "included_deals": 1,
                    "overage_price": 145
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 1800,  # 10 months price (2 months free)
                    "included_deals": 12,
                    "overage_price": 145
                }
            },
            SubscriptionTier.PRO: {
                BillingPeriod.MONTHLY: {
                    "base_price": 360,
                    "included_deals": 2,
                    "overage_price": 120
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 3600,  # 10 months price (2 months free)
                    "included_deals": 24,
                    "overage_price": 120
                }
            },
            SubscriptionTier.ENTERPRISE: {
                BillingPeriod.MONTHLY: {
                    "base_price": 1200,
                    "included_deals": 10,
                    "overage_price": 95
                },
                BillingPeriod.ANNUAL: {
                    "base_price": 12000,  # 10 months price
                    "included_deals": 120,
                    "overage_price": 95
                }
            }
        }

        # Currency conversion multipliers (approximate, update with real-time rates in production)
        currency_multipliers = {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.81,
            "NGN": 416.0,  # Nigerian Naira
            "AED": 3.67,   # UAE Dirham
            "ZAR": 18.5,   # South African Rand
            "KES": 130.0,  # Kenyan Shilling
            "GHS": 12.0,   # Ghanaian Cedi
            "EGP": 31.0,   # Egyptian Pound
            "SAR": 3.75,   # Saudi Riyal
            "QAR": 3.64,   # Qatari Riyal
        }

        # Get base pricing in USD
        usd_pricing = base_pricing_usd[tier][billing_period]

        # Convert to requested currency
        multiplier = currency_multipliers.get(currency.upper(), 1.0)

        return {
            "base_price": round(usd_pricing["base_price"] * multiplier, 2),
            "included_deals": usd_pricing["included_deals"],
            "overage_price": round(usd_pricing["overage_price"] * multiplier, 2),
            "currency": currency.upper()
        }
