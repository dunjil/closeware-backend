from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class CorrespondenceType(str, enum.Enum):
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    QUESTION = "question"
    ANSWER = "answer"
    CLARIFICATION = "clarification"


class Correspondence(Base):
    __tablename__ = "correspondence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)

    correspondence_type = Column(Enum(CorrespondenceType), nullable=False)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)

    correspondence_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deal = relationship("Deal", back_populates="correspondence")
