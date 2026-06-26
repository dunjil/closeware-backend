from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.organization import OrganizationCreate, Organization as OrganizationSchema
from app.models.organization import Organization

router = APIRouter()


@router.post("/", response_model=OrganizationSchema, status_code=status.HTTP_201_CREATED)
async def create_organization(org_data: OrganizationCreate, db: Session = Depends(get_db)):
    new_org = Organization(**org_data.dict())
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    return new_org
