"""
Complete signup and authentication system with:
- Combined org + user + trial creation
- Email verification
- Password reset
- Concurrent operation protection
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from uuid import UUID

from app.db.base import get_db
from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendVerificationRequest
)
from app.models.user import User, UserRole, UserType
from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.models.verification_token import VerificationToken, TokenType
from app.core.security import get_password_hash, verify_password
from app.core.validation import validate_email, sanitize_string
from app.services.email_service import email_service

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(signup_data: SignupRequest, db: Session = Depends(get_db)):
    """
    Complete signup flow:
    1. Create organization
    2. Create user (owner role, email_verified=False)
    3. Create Pro trial subscription (30 days)
    4. Send verification email

    BLOCKER FIX: This replaces the separate org + user registration flow
    """
    # Validate and sanitize inputs
    email = validate_email(signup_data.email)
    company_name = sanitize_string(signup_data.company_name, max_length=100)
    full_name = sanitize_string(signup_data.full_name, max_length=100)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    try:
        # Step 1: Create organization
        new_org = Organization(name=company_name)
        db.add(new_org)
        db.flush()  # Get org.id without committing

        # Step 2: Create owner user (not verified yet)
        hashed_password = get_password_hash(signup_data.password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            phone=signup_data.phone,
            user_type=UserType.INTERNAL,
            role=UserRole.OWNER,
            organization_id=new_org.id,
            email_verified=False,  # CRITICAL: User must verify email before full access
            is_active=True  # Can login, but some features blocked until verified
        )
        db.add(new_user)
        db.flush()

        # Step 3: Create FREE tier subscription (permanent, no trial)
        # New users start on FREE tier with 2 deals/month
        from app.models.subscription import BillingPeriod

        now = datetime.utcnow()
        period_end = now + timedelta(days=30)  # First billing period
        pricing = Subscription.get_tier_pricing(SubscriptionTier.FREE, BillingPeriod.MONTHLY)

        subscription = Subscription(
            organization_id=new_org.id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,  # FREE is always active
            billing_period=BillingPeriod.MONTHLY,
            currency="USD",
            base_price=pricing["base_price"],  # $0
            deal_limit=pricing["deal_limit"],  # 2 deals/month
            current_period_start=now,
            current_period_end=period_end,
            trial_ends_at=None  # No trial, FREE is permanent
        )
        db.add(subscription)
        db.flush()

        # Step 4: Create email verification token
        token = VerificationToken.generate_token()
        verification_token = VerificationToken(
            user_id=new_user.id,
            token=token,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=VerificationToken.get_expiry(TokenType.EMAIL_VERIFICATION)
        )
        db.add(verification_token)

        # Commit everything in one transaction
        db.commit()
        db.refresh(new_user)
        db.refresh(new_org)

        # Step 5: Send verification email (non-blocking)
        try:
            email_service.send_verification_email(
                user_email=new_user.email,
                user_name=new_user.full_name,
                token=token
            )
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")
            # Don't fail signup if email fails - user can resend

        return SignupResponse(
            user_id=str(new_user.id),
            email=new_user.email,
            full_name=new_user.full_name,
            organization_id=str(new_org.id),
            organization_name=new_org.name,
            message="Account created successfully! Check your email to verify your account and unlock all features."
        )

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account. Email may already be in use."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during signup: {str(e)}"
        )


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify user's email address using token from email.
    CRITICAL FIX: Internal users must verify email (like external users do via invite)
    """
    token = db.query(VerificationToken).filter(
        VerificationToken.token == request.token,
        VerificationToken.token_type == TokenType.EMAIL_VERIFICATION
    ).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid verification link"
        )

    if not token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has expired or already been used. Request a new one."
        )

    # Mark token as used
    token.mark_used()

    # Verify user's email
    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.email_verified = True
    user.updated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "message": "Email verified successfully! You can now access all features."
    }


@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email to user"""
    email = validate_email(request.email)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists (security)
        return {
            "success": True,
            "message": "If an account exists with this email, a verification link has been sent."
        }

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Invalidate old tokens (mark as used)
    old_tokens = db.query(VerificationToken).filter(
        VerificationToken.user_id == user.id,
        VerificationToken.token_type == TokenType.EMAIL_VERIFICATION,
        VerificationToken.used_at.is_(None)
    ).all()

    for old_token in old_tokens:
        old_token.mark_used()

    # Create new token
    token = VerificationToken.generate_token()
    verification_token = VerificationToken(
        user_id=user.id,
        token=token,
        token_type=TokenType.EMAIL_VERIFICATION,
        expires_at=VerificationToken.get_expiry(TokenType.EMAIL_VERIFICATION)
    )
    db.add(verification_token)
    db.commit()

    # Send email
    try:
        email_service.send_verification_email(
            user_email=user.email,
            user_name=user.full_name,
            token=token
        )
    except Exception as e:
        print(f"Failed to send verification email: {str(e)}")

    return {
        "success": True,
        "message": "Verification email sent! Check your inbox."
    }


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send password reset email.
    CRITICAL FIX: Users can now recover locked accounts
    """
    email = validate_email(request.email)

    user = db.query(User).filter(User.email == email).first()

    # Always return success (don't reveal if email exists - security)
    if not user:
        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent."
        }

    # Invalidate old tokens
    old_tokens = db.query(VerificationToken).filter(
        VerificationToken.user_id == user.id,
        VerificationToken.token_type == TokenType.PASSWORD_RESET,
        VerificationToken.used_at.is_(None)
    ).all()

    for old_token in old_tokens:
        old_token.mark_used()

    # Create reset token
    token = VerificationToken.generate_token()
    reset_token = VerificationToken(
        user_id=user.id,
        token=token,
        token_type=TokenType.PASSWORD_RESET,
        expires_at=VerificationToken.get_expiry(TokenType.PASSWORD_RESET)
    )
    db.add(reset_token)
    db.commit()

    # Send email
    try:
        email_service.send_password_reset_email(
            user_email=user.email,
            user_name=user.full_name,
            token=token
        )
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")

    return {
        "success": True,
        "message": "If an account exists with this email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password using token from email"""
    token = db.query(VerificationToken).filter(
        VerificationToken.token == request.token,
        VerificationToken.token_type == TokenType.PASSWORD_RESET
    ).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid reset link"
        )

    if not token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link has expired or already been used. Request a new one."
        )

    # Mark token as used
    token.mark_used()

    # Update password
    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.hashed_password = get_password_hash(request.new_password)
    user.updated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "message": "Password reset successfully! You can now log in with your new password."
    }
