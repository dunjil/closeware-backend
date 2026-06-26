from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.correspondence import CorrespondenceType


class CorrespondenceBase(BaseModel):
    correspondence_type: CorrespondenceType
    sender: str
    recipient: str
    subject: Optional[str] = None
    content: str
    correspondence_date: datetime


class CorrespondenceCreate(CorrespondenceBase):
    deal_id: UUID


class Correspondence(CorrespondenceBase):
    id: UUID
    deal_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
