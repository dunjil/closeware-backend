"""Input validation utilities"""
from typing import Optional
from fastapi import HTTPException, status
import re


def validate_email(email: str) -> str:
    """Validate email format"""
    email = email.strip().lower()
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    return email


def validate_password(password: str) -> str:
    """Validate password strength"""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if len(password) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be less than 72 characters"
        )
    return password


def validate_file_upload(
    filename: str,
    file_size: int,
    mime_type: str,
    max_size_mb: int = 10
) -> None:
    """Validate uploaded file"""
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/png',
        'image/jpg'
    ]

    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{mime_type}' not allowed. Accepted: PDF, Word, Images"
        )

    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {max_size_mb}MB limit"
        )

    # Check for dangerous file extensions
    dangerous_extensions = ['.exe', '.sh', '.bat', '.cmd', '.com', '.scr']
    if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed for security reasons"
        )


def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Sanitize and trim string input"""
    if value is None:
        return None
    value = value.strip()
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input exceeds maximum length of {max_length} characters"
        )
    return value if value else None
