from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.discrepancy_report import DiscrepancyStatus


class DiscrepancyItemBase(BaseModel):
    status: DiscrepancyStatus
    category: str
    description: str
    source_reference: Optional[Dict[str, Any]] = None
    suggested_fix: Optional[str] = None


class DiscrepancyItem(DiscrepancyItemBase):
    id: UUID
    report_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DiscrepancyReportBase(BaseModel):
    summary: Optional[Dict[str, Any]] = None


class DiscrepancyReport(DiscrepancyReportBase):
    id: UUID
    deal_id: UUID
    contract_draft_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscrepancyReportResponse(DiscrepancyReport):
    items: List[DiscrepancyItem] = []
