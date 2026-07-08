from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    letterhead_config = Column(JSON, nullable=True)

    # Credits system
    credit_balance = Column(Integer, default=0, nullable=False)  # Current credit balance
    is_early_adopter = Column(Boolean, default=False, nullable=False)  # Locked in 50% off forever
    early_adopter_number = Column(Integer, nullable=True)  # Customer #1, #2, etc. (1-100)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    deals = relationship("Deal", back_populates="organization")
    subscription = relationship("Subscription", back_populates="organization", uselist=False)
    credit_transactions = relationship("CreditTransaction", back_populates="organization", order_by="CreditTransaction.created_at.desc()")
