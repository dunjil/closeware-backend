"""
Status Change Logger Utility
Automatically logs contract status changes to audit trail.
"""
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.contract_draft import ContractDraft, DraftStatus
from app.models.contract_status_history import ContractStatusHistory
from app.models.user import User


def log_status_change(
    db: Session,
    contract_draft: ContractDraft,
    new_status: DraftStatus,
    changed_by: User,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> ContractStatusHistory:
    """
    Log a contract status change to the audit trail.

    This should be called BEFORE updating the contract status.

    Args:
        db: Database session
        contract_draft: The contract being updated
        new_status: The new status to set
        changed_by: User making the change
        reason: Optional reason for the change
        ip_address: Optional IP address of the request
        user_agent: Optional user agent of the request

    Returns:
        The created ContractStatusHistory entry
    """
    # Get old status before change
    old_status = contract_draft.status.value if contract_draft.status else None

    # Create history entry
    history_entry = ContractStatusHistory(
        contract_draft_id=contract_draft.id,
        old_status=old_status,
        new_status=new_status.value,
        changed_by_id=changed_by.id,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent
    )

    db.add(history_entry)
    # Don't commit - let the calling function handle the transaction

    return history_entry


def update_status_with_logging(
    db: Session,
    contract_draft: ContractDraft,
    new_status: DraftStatus,
    changed_by: User,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> ContractStatusHistory:
    """
    Update contract status AND log the change in one operation.

    This is the recommended way to change contract statuses.

    Args:
        db: Database session
        contract_draft: The contract to update
        new_status: The new status to set
        changed_by: User making the change
        reason: Optional reason for the change
        ip_address: Optional IP address
        user_agent: Optional user agent

    Returns:
        The created ContractStatusHistory entry
    """
    # Log the change BEFORE updating
    history_entry = log_status_change(
        db=db,
        contract_draft=contract_draft,
        new_status=new_status,
        changed_by=changed_by,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Update the status
    contract_draft.status = new_status

    return history_entry
