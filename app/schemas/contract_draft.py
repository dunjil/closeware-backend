from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class ContractDraftBase(BaseModel):
    title: str
    content: str


class ContractDraftCreate(ContractDraftBase):
    deal_id: UUID


class ContractDraft(ContractDraftBase):
    id: UUID
    deal_id: UUID
    version: int
    status: str
    current_reviewer_id: Optional[UUID] = None
    sent_externally_at: Optional[datetime] = None
    sent_to_party: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
