from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class DraftStatus(str, enum.Enum):
    INTERNAL_DRAFT = "internal_draft"  # Working copy, not sent
    PENDING_INTERNAL_REVIEW = "pending_internal_review"  # Sent to boss/reviewer
    PENDING_REVISIONS = "pending_revisions"  # Sent back to creator for fixes
    SENT_TO_COUNTERPARTY = "sent_to_counterparty"  # Sent externally
    AWAITING_COUNTERPARTY_RESPONSE = "awaiting_counterparty_response"  # External, waiting for response
    APPROVED = "approved"  # Final approved version
    READY_FOR_SIGNING = "ready_for_signing"  # Ready to collect signatures
    AWAITING_SIGNATURES = "awaiting_signatures"  # Signature requests sent
    PARTIALLY_SIGNED = "partially_signed"  # Some but not all signed
    FULLY_EXECUTED = "fully_executed"  # All signatures collected


class ContractDraft(Base):
    __tablename__ = "contract_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)

    version = Column(Integer, nullable=False, default=1)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # Workflow tracking
    status = Column(Enum(DraftStatus), nullable=False, default=DraftStatus.INTERNAL_DRAFT)
    current_reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sent_externally_at = Column(DateTime, nullable=True)
    sent_to_party = Column(String, nullable=True)  # Name of external party it was sent to

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deal = relationship("Deal", back_populates="contract_drafts")
    current_reviewer = relationship("User", foreign_keys=[current_reviewer_id])
    discrepancy_reports = relationship("DiscrepancyReport", back_populates="contract_draft", cascade="all, delete-orphan")
    signatures = relationship("Signature", back_populates="contract_draft", cascade="all, delete-orphan")
    internal_reviews = relationship("InternalReview", back_populates="contract_draft", cascade="all, delete-orphan")
    signature_requests = relationship("SignatureRequest", back_populates="contract_draft", cascade="all, delete-orphan")
    status_history = relationship("ContractStatusHistory", back_populates="contract_draft", cascade="all, delete-orphan", order_by="ContractStatusHistory.changed_at.desc()")
