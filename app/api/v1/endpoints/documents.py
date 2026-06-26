from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
from app.db.base import get_db
from app.schemas.document import DocumentCreate, DocumentResponse
from app.models.document import Document

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    deal_id: UUID,
    document_type: str,
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    from app.core.validation import validate_file_upload, sanitize_string
    from app.models.deal import Deal

    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )

    # Validate title
    title = sanitize_string(title, max_length=200)
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document title is required"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file
    validate_file_upload(
        filename=file.filename or "unknown",
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream"
    )

    # Save file with safe filename
    safe_filename = f"{UUID.uuid4()}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    new_doc = Document(
        deal_id=deal_id,
        document_type=document_type,
        title=title,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return DocumentResponse(**new_doc.__dict__, download_url=f"/api/v1/documents/{new_doc.id}/download")


@router.get("/deal/{deal_id}", response_model=List[DocumentResponse])
async def list_documents(deal_id: UUID, db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.deal_id == deal_id).all()
    return [DocumentResponse(**doc.__dict__, download_url=f"/api/v1/documents/{doc.id}/download") for doc in docs]


@router.get("/{document_id}/download")
async def download_document(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type,
        filename=doc.title
    )
