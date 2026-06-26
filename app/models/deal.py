from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class DealType(str, enum.Enum):
    PROPERTY = "property"
    CORPORATE_MA = "corporate_ma"
    JV_AGREEMENT = "jv_agreement"
    NDA_ONLY = "nda_only"


class DealStatus(str, enum.Enum):
    DRAFT = "draft"
    NEGOTIATING = "negotiating"
    VERIFICATION = "verification"
    REVIEW = "review"
    APPROVED = "approved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Deal(Base):
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    deal_type = Column(Enum(DealType), nullable=False)
    status = Column(Enum(DealStatus), nullable=False, default=DealStatus.DRAFT)

    title = Column(String, nullable=False)
    asset_description = Column(Text, nullable=True)
    agreed_price = Column(Numeric(precision=15, scale=2), nullable=True)
    currency = Column(String(3), nullable=True)

    parties = Column(JSONB, nullable=True)
    terms = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="deals")
    creator = relationship("User", back_populates="deals_created", foreign_keys=[creator_id])
    correspondence = relationship("Correspondence", back_populates="deal", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="deal", cascade="all, delete-orphan")
    contract_drafts = relationship("ContractDraft", back_populates="deal", cascade="all, delete-orphan")
    discrepancy_reports = relationship("DiscrepancyReport", back_populates="deal", cascade="all, delete-orphan")
    internal_reviews = relationship("InternalReview", back_populates="deal", cascade="all, delete-orphan")
    collaborators = relationship("DealCollaborator", back_populates="deal", cascade="all, delete-orphan")
