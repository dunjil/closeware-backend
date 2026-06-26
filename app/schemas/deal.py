from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from app.models.deal import DealType, DealStatus


class DealBase(BaseModel):
    deal_type: DealType
    title: str
    asset_description: Optional[str] = None
    agreed_price: Optional[Decimal] = None
    currency: Optional[str] = None
    parties: Optional[Dict[str, Any]] = None
    terms: Optional[Dict[str, Any]] = None


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    title: Optional[str] = None
    asset_description: Optional[str] = None
    agreed_price: Optional[Decimal] = None
    currency: Optional[str] = None
    parties: Optional[Dict[str, Any]] = None
    terms: Optional[Dict[str, Any]] = None
    status: Optional[DealStatus] = None


class Deal(DealBase):
    id: UUID
    organization_id: UUID
    creator_id: UUID
    status: DealStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DealResponse(Deal):
    correspondence_count: int = 0
    documents_count: int = 0
    latest_draft_version: Optional[int] = None
