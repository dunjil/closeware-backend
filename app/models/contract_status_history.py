from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class ContractStatusHistory(Base):
    """
    Tracks all status changes for contract drafts.
    Critical for audit trail and compliance.
    """
    __tablename__ = "contract_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_draft_id = Column(UUID(as_uuid=True), ForeignKey("contract_drafts.id", ondelete="CASCADE"), nullable=False)

    # Status change details
    old_status = Column(String, nullable=True)  # Null for initial creation
    new_status = Column(String, nullable=False)

    # Who made the change
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Why the change was made
    reason = Column(Text, nullable=True)  # Optional note about why status changed

    # Audit fields
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relationships
    contract_draft = relationship("ContractDraft", back_populates="status_history")
    changed_by = relationship("User")
