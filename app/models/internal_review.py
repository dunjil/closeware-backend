from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class ReviewAction(str, enum.Enum):
    REQUEST_REVIEW = "request_review"  # Sent to reviewer for approval
    REQUEST_REVISIONS = "request_revisions"  # Reviewer sends back for fixes
    APPROVE = "approve"  # Reviewer approves
    COMMENT = "comment"  # General comment/note
    SEND_EXTERNAL = "send_external"  # Sent to counterparty


# Valid state transitions for workflow enforcement
VALID_TRANSITIONS = {
    # From INTERNAL_DRAFT
    "internal_draft": ["pending_internal_review", "sent_to_counterparty"],

    # From PENDING_INTERNAL_REVIEW
    "pending_internal_review": ["pending_revisions", "approved", "internal_draft"],

    # From PENDING_REVISIONS
    "pending_revisions": ["pending_internal_review", "internal_draft"],

    # From APPROVED
    "approved": ["sent_to_counterparty", "internal_draft"],  # Can reopen or send

    # From SENT_TO_COUNTERPARTY
    "sent_to_counterparty": ["awaiting_counterparty_response", "internal_draft"],

    # From AWAITING_COUNTERPARTY_RESPONSE
    "awaiting_counterparty_response": ["internal_draft", "approved"],  # Back to draft for changes or mark approved
}


class InternalReview(Base):
    __tablename__ = "internal_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_draft_id = Column(UUID(as_uuid=True), ForeignKey("contract_drafts.id"), nullable=False)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)

    action = Column(Enum(ReviewAction), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Who it's assigned to

    comment = Column(Text, nullable=True)  # Reviewer's feedback/instructions

    # Audit trail
    draft_version = Column(Integer, nullable=False)  # Which version of draft was reviewed
    previous_status = Column(String, nullable=True)  # Status before this action
    new_status = Column(String, nullable=False)  # Status after this action
    ip_address = Column(String, nullable=True)  # For compliance/audit
    user_agent = Column(String, nullable=True)  # For compliance/audit

    # External party tracking (when action = SEND_EXTERNAL)
    sent_to_party_name = Column(String, nullable=True)  # Name of counterparty contact
    sent_to_party_email = Column(String, nullable=True)  # Email of counterparty contact

    created_at = Column(DateTime, default=datetime.utcnow)

    contract_draft = relationship("ContractDraft", back_populates="internal_reviews")
    deal = relationship("Deal", back_populates="internal_reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])
