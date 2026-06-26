from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db.base import get_db
from app.schemas.correspondence import CorrespondenceCreate, Correspondence as CorrespondenceSchema
from app.models.correspondence import Correspondence

router = APIRouter()


@router.post("/", response_model=CorrespondenceSchema, status_code=status.HTTP_201_CREATED)
async def create_correspondence(corr_data: CorrespondenceCreate, db: Session = Depends(get_db)):
    new_corr = Correspondence(**corr_data.dict())
    db.add(new_corr)
    db.commit()
    db.refresh(new_corr)
    return new_corr


@router.get("/deal/{deal_id}", response_model=List[CorrespondenceSchema])
async def list_correspondence(deal_id: UUID, db: Session = Depends(get_db)):
    items = db.query(Correspondence).filter(Correspondence.deal_id == deal_id).order_by(Correspondence.correspondence_date.desc()).all()
    return items
