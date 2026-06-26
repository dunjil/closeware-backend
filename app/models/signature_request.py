from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.base import Base


class SignatureRole(str, enum.Enum):
    BUYER = "buyer"           # Purchasing party
    SELLER = "seller"         # Selling party
    WITNESS = "witness"       # Witness to agreement
    GUARANTOR = "guarantor"   # Financial guarantor
    OTHER = "other"           # Other signatory


class SignatureRequestStatus(str, enum.Enum):
    PENDING = "pending"       # Request sent, not signed yet
    SIGNED = "signed"         # Signature collected
    DECLINED = "declined"     # Signer declined to sign
    EXPIRED = "expired"       # Request expired


class SignatureRequest(Base):
    """
    Tracks who needs to sign a contract.
    Created when contract is marked 'Ready for Signing'.
    """
    __tablename__ = "signature_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_draft_id = Column(UUID(as_uuid=True), ForeignKey("contract_drafts.id", ondelete="CASCADE"), nullable=False)

    # Who needs to sign
    signer_name = Column(String, nullable=False)
    signer_email = Column(String, nullable=False)
    signer_title = Column(String, nullable=True)
    signer_role = Column(Enum(SignatureRole), nullable=False)

    # Request details
    status = Column(Enum(SignatureRequestStatus), nullable=False, default=SignatureRequestStatus.PENDING)
    request_message = Column(String, nullable=True)

    # Tracking
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Completion
    signature_id = Column(UUID(as_uuid=True), ForeignKey("signatures.id"), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(String, nullable=True)

    # Relationships
    contract_draft = relationship("ContractDraft", back_populates="signature_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    signature = relationship("Signature")

    def is_pending(self) -> bool:
        """Check if signature is still pending"""
        if self.status != SignatureRequestStatus.PENDING:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def mark_signed(self, signature_id: UUID):
        """Mark request as signed"""
        self.status = SignatureRequestStatus.SIGNED
        self.signature_id = signature_id
        self.signed_at = datetime.utcnow()

    def mark_declined(self, reason: str = None):
        """Mark request as declined"""
        self.status = SignatureRequestStatus.DECLINED
        self.declined_at = datetime.utcnow()
        self.decline_reason = reason
