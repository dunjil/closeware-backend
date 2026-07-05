from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_draft_id = Column(String, ForeignKey("contract_drafts.id", ondelete="CASCADE"), nullable=False)
    signer_name = Column(String, nullable=False)
    signer_title = Column(String, nullable=False)
    signer_email = Column(String, nullable=True)
    signature_data = Column(Text, nullable=False)  # SVG path or base64 image
    signature_type = Column(String, default="drawn")  # drawn, typed, uploaded
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_buyer = Column(Boolean, default=True)  # True for buyer, False for seller

    # Relationships
    contract_draft = relationship("ContractDraft", back_populates="signatures")
