from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class CollaboratorRole(str, enum.Enum):
    OWNER = "owner"  # Deal owner (internal)
    COLLABORATOR = "collaborator"  # Internal team member
    EXTERNAL_REVIEWER = "external_reviewer"  # External party who can view/comment
    EXTERNAL_SIGNER = "external_signer"  # External party who needs to sign


class DealCollaborator(Base):
    """
    Links users (internal or external) to specific deals with granular permissions.
    Internal users can access all deals in their org (via organization_id).
    External users only see deals they're explicitly added to via this table.
    """
    __tablename__ = "deal_collaborators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(Enum(CollaboratorRole), nullable=False, default=CollaboratorRole.EXTERNAL_REVIEWER)

    # Granular permissions (can override defaults by role)
    permissions = Column(JSONB, nullable=True)
    # Example: {"can_view_docs": true, "can_comment": true, "can_upload_docs": false, "can_view_internal_reviews": false}

    # Invitation tracking
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    invited_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)  # When they accepted/first accessed

    # Engagement tracking
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(String, default="0")  # Track how often they view

    # Status
    is_active = Column(String, default="true")  # Can revoke access by setting to false

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id], back_populates="deal_collaborations")
    inviter = relationship("User", foreign_keys=[invited_by])
