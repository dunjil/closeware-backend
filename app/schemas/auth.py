from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class SignupRequest(BaseModel):
    """Combined signup - creates organization + user + trial"""
    # Organization details
    company_name: str

    # User details
    email: EmailStr
    password: str
    full_name: str

    # Optional
    phone: Optional[str] = None

    @validator('company_name')
    def validate_company_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Company name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Company name must be less than 100 characters')
        return v.strip()

    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Full name must be less than 100 characters')
        return v.strip()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class SignupResponse(BaseModel):
    """Response after successful signup"""
    user_id: str
    email: str
    full_name: str
    organization_id: str
    organization_name: str
    message: str = "Account created successfully. Please check your email to verify your account."


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class ResendVerificationRequest(BaseModel):
    email: EmailStr
