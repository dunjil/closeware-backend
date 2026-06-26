from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.base import get_db
from app.schemas.discrepancy_report import DiscrepancyReportResponse
from app.models.contract_draft import ContractDraft
from app.models.deal import Deal
from app.services.comparison_engine import ComparisonEngine

router = APIRouter()


@router.post("/compare/{contract_draft_id}", response_model=DiscrepancyReportResponse)
async def run_comparison(contract_draft_id: UUID, db: Session = Depends(get_db)):
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract draft not found")

    deal = db.query(Deal).filter(Deal.id == draft.deal_id).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    engine = ComparisonEngine()
    report = engine.compare_contract_to_trail(draft, deal, db)

    db.refresh(report)

    return DiscrepancyReportResponse(
        id=report.id,
        deal_id=report.deal_id,
        contract_draft_id=report.contract_draft_id,
        summary=report.summary,
        created_at=report.created_at,
        updated_at=report.updated_at,
        items=report.items
    )


@router.get("/reports/deal/{deal_id}", response_model=list[DiscrepancyReportResponse])
async def get_deal_reports(deal_id: UUID, db: Session = Depends(get_db)):
    from app.models.discrepancy_report import DiscrepancyReport

    reports = db.query(DiscrepancyReport).filter(DiscrepancyReport.deal_id == deal_id).all()

    return [
        DiscrepancyReportResponse(
            id=r.id,
            deal_id=r.deal_id,
            contract_draft_id=r.contract_draft_id,
            summary=r.summary,
            created_at=r.created_at,
            updated_at=r.updated_at,
            items=r.items
        ) for r in reports
    ]
