from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models import (
    User, Deal, PendingExternalUser, DealCollaborator,
    InviteStatus, UserType, CollaboratorRole
)
from app.schemas.external_invite import (
    ExternalInviteCreate, ExternalInviteResponse,
    ValidateInviteResponse, CompleteSignupRequest,
    DealCollaboratorResponse
)
from app.api.dependencies import get_current_user
from app.services.permissions import PermissionService
from app.services.email_service import email_service
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/deals/{deal_id}/invite-external", response_model=ExternalInviteResponse)
def invite_external_user(
    deal_id: UUID,
    invite: ExternalInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Invite an external user to access a deal.

    - If user already has an account, grants them access immediately
    - If user is new, creates a pending invite and sends signup email
    """
    # Verify deal exists and user has permission
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Only internal users can invite external collaborators
    if current_user.user_type != UserType.INTERNAL:
        raise HTTPException(
            status_code=403,
            detail="Only internal team members can invite external collaborators"
        )

    if not PermissionService.can_access_deal(current_user, deal_id, db):
        raise HTTPException(status_code=403, detail="You don't have access to this deal")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == invite.email).first()

    if existing_user:
        # User already has account - just grant access
        # Check if they're already a collaborator
        existing_collab = (
            db.query(DealCollaborator)
            .filter(
                DealCollaborator.deal_id == deal_id,
                DealCollaborator.user_id == existing_user.id
            )
            .first()
        )

        if existing_collab:
            raise HTTPException(
                status_code=400,
                detail=f"{invite.email} is already a collaborator on this deal"
            )

        # Create collaborator record
        collaborator = DealCollaborator(
            deal_id=deal_id,
            user_id=existing_user.id,
            role=CollaboratorRole(invite.role),
            invited_by=current_user.id,
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),  # Immediately accepted for existing users
        )
        db.add(collaborator)
        db.commit()

        # Send email notification to existing user
        email_service.send_external_user_added_to_deal(
            user=existing_user,
            deal=deal,
            inviter=current_user,
            message=invite.message
        )

        # Return invite-like response (even though no actual invite was created)
        return ExternalInviteResponse(
            id=collaborator.id,
            email=existing_user.email,
            name=existing_user.full_name,
            invite_token=collaborator.id,  # Use collaborator ID as token
            deal_id=deal_id,
            status="accepted",
            expires_at=datetime.utcnow() + timedelta(days=365),  # Not actually used
            created_at=collaborator.created_at
        )

    else:
        # User doesn't exist - create pending invite
        # Check for existing pending invite
        existing_invite = (
            db.query(PendingExternalUser)
            .filter(
                PendingExternalUser.email == invite.email,
                PendingExternalUser.invited_to_deal_id == deal_id,
                PendingExternalUser.status == InviteStatus.PENDING
            )
            .first()
        )

        if existing_invite and not existing_invite.is_expired():
            raise HTTPException(
                status_code=400,
                detail=f"An active invitation for {invite.email} already exists for this deal"
            )

        # Create new invite
        pending_invite = PendingExternalUser(
            email=invite.email,
            name=invite.name,
            organization_name=invite.organization_name,
            title=invite.title,
            invited_to_deal_id=deal_id,
            invited_by=current_user.id,
            message=invite.message,
            collaborator_role=invite.role,
            status=InviteStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(pending_invite)
        db.commit()
        db.refresh(pending_invite)

        # Send invitation email
        email_service.send_external_invite_new_user(
            invite=pending_invite,
            deal=deal,
            inviter=current_user
        )

        return ExternalInviteResponse(
            id=pending_invite.id,
            email=pending_invite.email,
            name=pending_invite.name,
            invite_token=pending_invite.invite_token,
            deal_id=deal_id,
            status=pending_invite.status.value,
            expires_at=pending_invite.expires_at,
            created_at=pending_invite.created_at
        )


@router.get("/validate-invite/{token}", response_model=ValidateInviteResponse)
def validate_invite(token: UUID, db: Session = Depends(get_db)):
    """
    Validate an invite token and return invitation details for signup page.
    No authentication required - public endpoint.
    """
    invite = (
        db.query(PendingExternalUser)
        .filter(PendingExternalUser.invite_token == token)
        .first()
    )

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if not invite.is_valid():
        if invite.status == InviteStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="This invitation has already been accepted")
        elif invite.is_expired():
            raise HTTPException(status_code=400, detail="This invitation has expired")
        else:
            raise HTTPException(status_code=400, detail="This invitation is no longer valid")

    # Get deal and inviter details
    deal = db.query(Deal).filter(Deal.id == invite.invited_to_deal_id).first()
    inviter = db.query(User).filter(User.id == invite.invited_by).first()

    if not deal or not inviter:
        raise HTTPException(status_code=500, detail="Invitation data is corrupted")

    return ValidateInviteResponse(
        is_valid=True,
        email=invite.email,
        name=invite.name,
        organization_name=invite.organization_name,
        title=invite.title,
        deal_title=deal.title,
        deal_id=deal.id,
        inviter_name=inviter.full_name,
        message=invite.message,
        expires_at=invite.expires_at
    )


@router.post("/complete-signup")
def complete_external_signup(
    signup: CompleteSignupRequest,
    db: Session = Depends(get_db),
):
    """
    Complete external user signup from an invitation.
    Creates user account and grants deal access.
    No authentication required - uses invite token.
    """
    # Validate invite
    invite = (
        db.query(PendingExternalUser)
        .filter(PendingExternalUser.invite_token == signup.invite_token)
        .first()
    )

    if not invite or not invite.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")

    # Check if email already has an account
    existing_user = db.query(User).filter(User.email == invite.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please log in instead."
        )

    # Create user account
    hashed_password = pwd_context.hash(signup.password)
    new_user = User(
        email=invite.email,
        hashed_password=hashed_password,
        full_name=invite.name,
        user_type=UserType.EXTERNAL,
        external_organization_name=invite.organization_name,
        title=invite.title,
        phone=signup.phone,
        email_verified=True,  # Email verified via invite token
        is_active=True,
        organization_id=None,  # External users don't belong to an organization
        role=None
    )
    db.add(new_user)
    db.flush()  # Get user ID without committing

    # Create deal collaborator record
    collaborator = DealCollaborator(
        deal_id=invite.invited_to_deal_id,
        user_id=new_user.id,
        role=CollaboratorRole(invite.collaborator_role),
        invited_by=invite.invited_by,
        invited_at=invite.created_at,
        accepted_at=datetime.utcnow()
    )
    db.add(collaborator)

    # Mark invite as accepted
    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.utcnow()
    invite.created_user_id = new_user.id

    db.commit()
    db.refresh(new_user)

    # Return success - frontend will redirect to login
    return {
        "message": "Account created successfully",
        "user_id": str(new_user.id),
        "email": new_user.email,
        "deal_id": str(invite.invited_to_deal_id)
    }


@router.get("/deals/{deal_id}/collaborators", response_model=List[DealCollaboratorResponse])
def get_deal_collaborators(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all collaborators on a deal (internal users only)"""
    # Only internal users can view collaborator list
    if current_user.user_type != UserType.INTERNAL:
        raise HTTPException(status_code=403, detail="Only internal users can view collaborators")

    if not PermissionService.can_access_deal(current_user, deal_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    collaborators = (
        db.query(DealCollaborator)
        .filter(DealCollaborator.deal_id == deal_id)
        .all()
    )

    result = []
    for collab in collaborators:
        user = db.query(User).filter(User.id == collab.user_id).first()
        if user:
            result.append(DealCollaboratorResponse(
                id=collab.id,
                deal_id=collab.deal_id,
                user_id=collab.user_id,
                role=collab.role.value if isinstance(collab.role, CollaboratorRole) else collab.role,
                user_name=user.full_name,
                user_email=user.email,
                user_organization=user.external_organization_name if user.user_type == UserType.EXTERNAL else user.organization.name if user.organization else None,
                invited_at=collab.invited_at,
                accepted_at=collab.accepted_at,
                last_accessed_at=collab.last_accessed_at
            ))

    return result
