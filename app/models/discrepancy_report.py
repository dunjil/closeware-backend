from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class DiscrepancyStatus(str, enum.Enum):
    MATCHED = "matched"
    FLAGGED = "flagged"
    MISSING = "missing"


class DiscrepancyReport(Base):
    __tablename__ = "discrepancy_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    contract_draft_id = Column(UUID(as_uuid=True), ForeignKey("contract_drafts.id"), nullable=False)

    summary = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deal = relationship("Deal", back_populates="discrepancy_reports")
    contract_draft = relationship("ContractDraft", back_populates="discrepancy_reports")
    items = relationship("DiscrepancyItem", back_populates="report", cascade="all, delete-orphan")


class DiscrepancyItem(Base):
    __tablename__ = "discrepancy_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("discrepancy_reports.id"), nullable=False)

    status = Column(Enum(DiscrepancyStatus), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    source_reference = Column(JSONB, nullable=True)
    suggested_fix = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("DiscrepancyReport", back_populates="items")
