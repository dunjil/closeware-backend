from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.models import InternalReview, ContractDraft, User, DraftStatus, ReviewAction
from app.schemas.internal_review import InternalReview as InternalReviewSchema, InternalReviewCreate
from app.api.dependencies import get_current_user
from app.services.workflow_manager import WorkflowManager, WorkflowError

router = APIRouter()


@router.post("", response_model=InternalReviewSchema)
def create_internal_review(
    review: InternalReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create an internal review action with full workflow validation:
    - request_review: Send to someone for approval
    - request_revisions: Send back for fixes
    - approve: Approve the draft
    - comment: Add a comment
    - send_external: Mark as sent to counterparty

    Enforces:
    - Valid state transitions
    - User permissions
    - Audit trail
    """
    # Verify draft exists
    draft = db.query(ContractDraft).filter(ContractDraft.id == review.contract_draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Contract draft not found")

    # Parse action enum
    try:
        action_enum = ReviewAction(review.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {review.action}")

    # Check user permissions
    can_action, reason = WorkflowManager.can_user_action_draft(current_user, draft, action_enum)
    if not can_action:
        raise HTTPException(status_code=403, detail=reason)

    # Get target status
    target_status = WorkflowManager.get_target_status_for_action(
        action_enum,
        draft.status.value if isinstance(draft.status, DraftStatus) else draft.status,
        review.reviewee_id
    )

    # Validate state transition
    try:
        WorkflowManager.validate_transition(
            draft.status.value if isinstance(draft.status, DraftStatus) else draft.status,
            target_status
        )
    except WorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Lookup reviewee if email provided
    reviewee_id = review.reviewee_id
    if hasattr(review, 'reviewee_email') and review.reviewee_email:
        reviewee = WorkflowManager.lookup_user_by_email(db, review.reviewee_email)
        if not reviewee:
            raise HTTPException(status_code=404, detail=f"User with email {review.reviewee_email} not found")
        reviewee_id = reviewee.id

    # Extract IP and user agent for audit
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Store previous status
    previous_status = draft.status.value if isinstance(draft.status, DraftStatus) else draft.status

    # Create the review record with full audit trail
    db_review = InternalReview(
        contract_draft_id=review.contract_draft_id,
        deal_id=review.deal_id,
        action=action_enum,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        comment=review.comment,
        draft_version=draft.version,
        previous_status=previous_status,
        new_status=target_status,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(db_review)

    # Update draft status based on action
    if action_enum == ReviewAction.REQUEST_REVIEW:
        draft.status = DraftStatus.PENDING_INTERNAL_REVIEW
        draft.current_reviewer_id = reviewee_id
    elif action_enum == ReviewAction.REQUEST_REVISIONS:
        draft.status = DraftStatus.PENDING_REVISIONS
        draft.current_reviewer_id = reviewee_id
    elif action_enum == ReviewAction.APPROVE:
        draft.status = DraftStatus.APPROVED
        draft.current_reviewer_id = None
    elif action_enum == ReviewAction.SEND_EXTERNAL:
        draft.status = DraftStatus.SENT_TO_COUNTERPARTY
        draft.sent_externally_at = datetime.utcnow()
        draft.current_reviewer_id = None
        # Extract external party info if provided
        if hasattr(review, 'sent_to_party_name'):
            db_review.sent_to_party_name = review.sent_to_party_name
            draft.sent_to_party = review.sent_to_party_name
        if hasattr(review, 'sent_to_party_email'):
            db_review.sent_to_party_email = review.sent_to_party_email

    db.commit()
    db.refresh(db_review)
    return db_review


@router.get("/draft/{draft_id}", response_model=List[InternalReviewSchema])
def get_draft_reviews(
    draft_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all internal reviews for a specific draft"""
    reviews = (
        db.query(InternalReview)
        .filter(InternalReview.contract_draft_id == draft_id)
        .order_by(InternalReview.created_at.desc())
        .all()
    )
    return reviews


@router.get("/deal/{deal_id}", response_model=List[InternalReviewSchema])
def get_deal_reviews(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all internal reviews for a deal"""
    reviews = (
        db.query(InternalReview)
        .filter(InternalReview.deal_id == deal_id)
        .order_by(InternalReview.created_at.desc())
        .all()
    )
    return reviews


@router.get("/pending", response_model=List[InternalReviewSchema])
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all drafts pending review by the current user"""
    drafts = (
        db.query(ContractDraft)
        .filter(ContractDraft.current_reviewer_id == current_user.id)
        .filter(
            ContractDraft.status.in_([
                DraftStatus.PENDING_INTERNAL_REVIEW,
                DraftStatus.PENDING_REVISIONS
            ])
        )
        .all()
    )

    # Get the latest review for each draft
    reviews = []
    for draft in drafts:
        latest_review = (
            db.query(InternalReview)
            .filter(InternalReview.contract_draft_id == draft.id)
            .order_by(InternalReview.created_at.desc())
            .first()
        )
        if latest_review:
            reviews.append(latest_review)

    return reviews
