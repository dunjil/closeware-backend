from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db.base import get_db
from app.schemas.contract_draft import ContractDraftCreate, ContractDraft as ContractDraftSchema
from app.models.contract_draft import ContractDraft

router = APIRouter()


@router.post("/", response_model=ContractDraftSchema, status_code=status.HTTP_201_CREATED)
async def create_contract_draft(draft_data: ContractDraftCreate, db: Session = Depends(get_db)):
    existing_drafts = db.query(ContractDraft).filter(ContractDraft.deal_id == draft_data.deal_id).all()
    next_version = max([d.version for d in existing_drafts], default=0) + 1

    new_draft = ContractDraft(
        deal_id=draft_data.deal_id,
        title=draft_data.title,
        content=draft_data.content,
        version=next_version
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)
    return new_draft


@router.get("/deal/{deal_id}", response_model=List[ContractDraftSchema])
async def list_contract_drafts(deal_id: UUID, db: Session = Depends(get_db)):
    drafts = db.query(ContractDraft).filter(ContractDraft.deal_id == deal_id).order_by(ContractDraft.version.desc()).all()
    return drafts


@router.get("/{draft_id}", response_model=ContractDraftSchema)
async def get_contract_draft(draft_id: UUID, db: Session = Depends(get_db)):
    draft = db.query(ContractDraft).filter(ContractDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract draft not found")
    return draft
