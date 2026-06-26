from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class UsageType(str, enum.Enum):
    CONTRACT_GENERATION = "contract_generation"  # AI generated a contract
    CONTRACT_VERIFICATION = "contract_verification"  # Ran verification/comparison
    CONTRACT_REGENERATION = "contract_regeneration"  # Regenerated with corrections


class UsageRecord(Base):
    """
    Tracks usage events for billing purposes.
    Each contract generation = 1 deal usage.
    """
    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # What was used
    usage_type = Column(Enum(UsageType), nullable=False)

    # Context
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    contract_draft_id = Column(UUID(as_uuid=True), ForeignKey("contract_drafts.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    description = Column(String, nullable=True)  # "Generated SPA for Reign Restaurant deal"

    # Billing period this belongs to
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="usage_records")
    organization = relationship("Organization")
    deal = relationship("Deal")
    contract_draft = relationship("ContractDraft")
    user = relationship("User")
