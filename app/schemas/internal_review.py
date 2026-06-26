from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional


class InternalReviewBase(BaseModel):
    action: str
    comment: Optional[str] = None


class InternalReviewCreate(InternalReviewBase):
    contract_draft_id: UUID
    deal_id: UUID
    reviewee_id: Optional[UUID] = None  # Who to assign to (by ID)
    reviewee_email: Optional[EmailStr] = None  # Or by email (will be looked up)
    sent_to_party_name: Optional[str] = None  # For SEND_EXTERNAL action
    sent_to_party_email: Optional[EmailStr] = None  # For SEND_EXTERNAL action


class InternalReview(InternalReviewBase):
    id: UUID
    contract_draft_id: UUID
    deal_id: UUID
    reviewer_id: UUID
    reviewee_id: Optional[UUID] = None
    draft_version: int
    previous_status: Optional[str] = None
    new_status: str
    ip_address: Optional[str] = None
    sent_to_party_name: Optional[str] = None
    sent_to_party_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
