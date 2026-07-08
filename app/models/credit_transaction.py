"""
Credit Transaction Model - Tracks all credit purchases and usage
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLAlchemyEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime

from app.db.base import Base


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"           # User bought credits
    USAGE = "usage"                 # Credits used for a deal
    ADMIN_GRANT = "admin_grant"     # Admin added credits
    ADMIN_DEDUCT = "admin_deduct"   # Admin removed credits
    REFUND = "refund"               # Refunded credits
    EXPIRY = "expiry"               # Credits expired


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transaction details
    transaction_type = Column(SQLAlchemyEnum(TransactionType), nullable=False, index=True)
    credits = Column(Integer, nullable=False)  # Positive for add, negative for deduct
    balance_after = Column(Integer, nullable=False)  # Credit balance after this transaction

    # Reference
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)  # If usage, which deal
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Who performed the action

    # Payment reference (if purchase)
    payment_reference = Column(String, nullable=True)  # Stripe payment ID, invoice number, etc.
    amount_paid = Column(Integer, nullable=True)  # Amount in cents (for purchases)

    # Admin actions
    admin_note = Column(Text, nullable=True)  # Admin's reason for granting/deducting

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="credit_transactions")
    deal = relationship("Deal", backref="credit_transaction")
    user = relationship("User", backref="credit_transactions")
