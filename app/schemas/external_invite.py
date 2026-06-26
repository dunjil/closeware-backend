from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional


class ExternalInviteCreate(BaseModel):
    """Request to invite an external user to a deal"""
    email: EmailStr
    name: str
    organization_name: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    role: str = "external_reviewer"  # external_reviewer or external_signer


class ExternalInviteResponse(BaseModel):
    """Response after sending invite"""
    id: UUID
    email: str
    name: str
    invite_token: UUID
    deal_id: UUID
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ValidateInviteResponse(BaseModel):
    """Response when validating an invite token"""
    is_valid: bool
    email: str
    name: str
    organization_name: Optional[str] = None
    title: Optional[str] = None
    deal_title: str
    deal_id: UUID
    inviter_name: str
    message: Optional[str] = None
    expires_at: datetime


class CompleteSignupRequest(BaseModel):
    """Request to complete external user signup"""
    invite_token: UUID
    password: str
    phone: Optional[str] = None


class DealCollaboratorResponse(BaseModel):
    """Deal collaborator information"""
    id: UUID
    deal_id: UUID
    user_id: UUID
    role: str
    user_name: str
    user_email: str
    user_organization: Optional[str] = None
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
