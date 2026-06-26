from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.document import DocumentType


class DocumentBase(BaseModel):
    document_type: DocumentType
    title: str
    document_metadata: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    deal_id: UUID


class Document(DocumentBase):
    id: UUID
    deal_id: UUID
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(Document):
    download_url: Optional[str] = None
