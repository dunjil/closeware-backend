"""
Workflow transition management and validation for internal review processes.
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import ContractDraft, User, DraftStatus, InternalReview, ReviewAction, VALID_TRANSITIONS


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""
    pass


class WorkflowManager:
    """Manages contract draft workflow state transitions and validation."""

    @staticmethod
    def validate_transition(current_status: str, target_status: str) -> None:
        """
        Validate that a status transition is allowed.

        Raises:
            WorkflowError: If transition is not valid
        """
        if current_status not in VALID_TRANSITIONS:
            raise WorkflowError(f"Unknown status: {current_status}")

        valid_targets = VALID_TRANSITIONS[current_status]
        if target_status not in valid_targets:
            raise WorkflowError(
                f"Cannot transition from '{current_status}' to '{target_status}'. "
                f"Valid transitions: {', '.join(valid_targets)}"
            )

    @staticmethod
    def get_target_status_for_action(
        action: ReviewAction,
        current_status: str,
        reviewee_id: Optional[UUID] = None
    ) -> str:
        """
        Determine the target status based on the review action.

        Args:
            action: The review action being performed
            current_status: Current draft status
            reviewee_id: User being assigned (for REQUEST_REVIEW/REQUEST_REVISIONS)

        Returns:
            Target status after action
        """
        if action == ReviewAction.REQUEST_REVIEW:
            return DraftStatus.PENDING_INTERNAL_REVIEW.value

        elif action == ReviewAction.REQUEST_REVISIONS:
            return DraftStatus.PENDING_REVISIONS.value

        elif action == ReviewAction.APPROVE:
            return DraftStatus.APPROVED.value

        elif action == ReviewAction.SEND_EXTERNAL:
            return DraftStatus.SENT_TO_COUNTERPARTY.value

        elif action == ReviewAction.COMMENT:
            # Comments don't change status
            return current_status

        else:
            raise WorkflowError(f"Unknown action: {action}")

    @staticmethod
    def can_user_action_draft(
        user: User,
        draft: ContractDraft,
        action: ReviewAction
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a user has permission to perform an action on a draft.

        Returns:
            Tuple of (is_allowed, reason_if_not_allowed)
        """
        # Anyone can add comments
        if action == ReviewAction.COMMENT:
            return True, None

        # REQUEST_REVIEW: only if you're the current owner/creator or it's unassigned
        if action == ReviewAction.REQUEST_REVIEW:
            if draft.current_reviewer_id is None or draft.current_reviewer_id == user.id:
                return True, None
            return False, "Draft is currently assigned to another reviewer"

        # REQUEST_REVISIONS or APPROVE: only if you're the assigned reviewer
        if action in [ReviewAction.REQUEST_REVISIONS, ReviewAction.APPROVE]:
            if draft.current_reviewer_id == user.id:
                return True, None
            return False, "Only the assigned reviewer can approve or request revisions"

        # SEND_EXTERNAL: only if draft is approved and you're authorized
        if action == ReviewAction.SEND_EXTERNAL:
            if draft.status != DraftStatus.APPROVED:
                return False, "Draft must be approved before sending externally"
            # You could add role checks here (e.g., only CEO can send)
            return True, None

        return False, "Action not permitted"

    @staticmethod
    def lookup_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Look up a user by email address for reviewer assignment.

        Args:
            db: Database session
            email: Email address to search for

        Returns:
            User if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()
