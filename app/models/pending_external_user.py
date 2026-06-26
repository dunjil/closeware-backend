from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
from app.db.base import Base


class InviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PendingExternalUser(Base):
    """
    Stores pending invitations for external users who don't have accounts yet.
    When they sign up via the invite link, this becomes a User record
    and a DealCollaborator record.
    """
    __tablename__ = "pending_external_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User details (pre-filled in signup form)
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    organization_name = Column(String, nullable=True)
    title = Column(String, nullable=True)

    # Deal they're invited to
    invited_to_deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)

    # Invitation metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    invite_token = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    message = Column(String, nullable=True)  # Optional message from inviter

    # Role they'll have once they accept
    collaborator_role = Column(String, nullable=False, default="external_reviewer")

    # Status
    status = Column(Enum(InviteStatus), nullable=False, default=InviteStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Track the created user (once accepted)
    created_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    deal = relationship("Deal")
    inviter = relationship("User", foreign_keys=[invited_by])
    created_user = relationship("User", foreign_keys=[created_user_id])

    def is_expired(self) -> bool:
        """Check if invite has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if invite is still valid for acceptance"""
        return (
            self.status == InviteStatus.PENDING
            and not self.is_expired()
        )

    @staticmethod
    def create_with_expiry(days=7, **kwargs):
        """Helper to create invite with default 7-day expiry"""
        return PendingExternalUser(
            expires_at=datetime.utcnow() + timedelta(days=days),
            **kwargs
        )
