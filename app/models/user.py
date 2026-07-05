from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class UserRole(str, enum.Enum):
    AGENT = "agent"
    REVIEWER = "reviewer"
    SIGNER = "signer"
    ADMIN = "admin"
    OWNER = "owner"


class UserType(str, enum.Enum):
    INTERNAL = "internal"  # Part of the organization (company employee)
    EXTERNAL = "external"  # External collaborator (seller's lawyer, etc.)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)

    # User type determines access model
    user_type = Column(Enum(UserType), nullable=False, default=UserType.INTERNAL)

    # For internal users
    role = Column(Enum(UserRole), nullable=True)  # Nullable for external users
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)  # Nullable for external

    # For external users
    external_organization_name = Column(String, nullable=True)  # "XYZ Law Firm"
    phone = Column(String, nullable=True)
    title = Column(String, nullable=True)  # "Senior Partner", "CFO", etc.

    # Account status
    email_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    deals_created = relationship("Deal", back_populates="creator", foreign_keys="Deal.creator_id")
    deal_collaborations = relationship("DealCollaborator", back_populates="user", cascade="all, delete-orphan")
