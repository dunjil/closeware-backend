from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.base import get_db
from app.models.contract_draft import ContractDraft
from app.models.discrepancy_report import DiscrepancyItem
from app.services.contract_fixer import ContractFixer
from app.schemas.contract_draft import ContractDraft as ContractDraftSchema
from pydantic import BaseModel
from typing import List

router = APIRouter()


class ApplySingleFixRequest(BaseModel):
    discrepancy_item_id: UUID


class ApplyMultipleFixesRequest(BaseModel):
    discrepancy_item_ids: List[UUID]


@router.post("/apply-fix/{contract_draft_id}", response_model=ContractDraftSchema)
async def apply_single_fix(
    contract_draft_id: UUID,
    request: ApplySingleFixRequest,
    db: Session = Depends(get_db)
):
    """
    Apply a single suggested fix to a contract draft, creating a new version.
    """
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract draft not found")

    discrepancy_item = db.query(DiscrepancyItem).filter(
        DiscrepancyItem.id == request.discrepancy_item_id
    ).first()
    if not discrepancy_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discrepancy item not found")

    if not discrepancy_item.suggested_fix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discrepancy item has no suggested fix"
        )

    fixer = ContractFixer()

    try:
        updated_content = fixer.apply_single_fix(draft, discrepancy_item, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply fix: {str(e)}"
        )

    # Create new version
    existing_drafts = db.query(ContractDraft).filter(ContractDraft.deal_id == draft.deal_id).all()
    next_version = max([d.version for d in existing_drafts], default=0) + 1

    new_draft = ContractDraft(
        deal_id=draft.deal_id,
        title=f"{draft.title} (Fix Applied)",
        content=updated_content,
        version=next_version
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    return new_draft


@router.post("/apply-fixes/{contract_draft_id}", response_model=ContractDraftSchema)
async def apply_multiple_fixes(
    contract_draft_id: UUID,
    request: ApplyMultipleFixesRequest,
    db: Session = Depends(get_db)
):
    """
    Apply multiple suggested fixes to a contract draft at once, creating a new version.
    """
    draft = db.query(ContractDraft).filter(ContractDraft.id == contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract draft not found")

    discrepancy_items = db.query(DiscrepancyItem).filter(
        DiscrepancyItem.id.in_(request.discrepancy_item_ids)
    ).all()

    if not discrepancy_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No discrepancy items found")

    # Verify all items have suggested fixes
    items_without_fixes = [
        item for item in discrepancy_items
        if not item.suggested_fix
    ]
    if items_without_fixes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{len(items_without_fixes)} item(s) have no suggested fix"
        )

    fixer = ContractFixer()

    try:
        updated_content = fixer.apply_multiple_fixes(draft, discrepancy_items, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply fixes: {str(e)}"
        )

    # Create new version
    existing_drafts = db.query(ContractDraft).filter(ContractDraft.deal_id == draft.deal_id).all()
    next_version = max([d.version for d in existing_drafts], default=0) + 1

    new_draft = ContractDraft(
        deal_id=draft.deal_id,
        title=f"{draft.title} (Fixes Applied)",
        content=updated_content,
        version=next_version
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    return new_draft
