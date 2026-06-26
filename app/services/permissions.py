"""
Permission and access control service for deals and documents.
Handles internal vs external user access patterns.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import User, Deal, DealCollaborator, UserType


class PermissionService:
    """Centralized permission checking for deal access"""

    @staticmethod
    def can_access_deal(user: User, deal_id: UUID, db: Session) -> bool:
        """
        Check if a user can access a specific deal.

        Internal users: Can access all deals in their organization
        External users: Can only access deals they're explicitly added to via DealCollaborator
        """
        # Get the deal
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return False

        # Internal users can access all deals in their org
        if user.user_type == UserType.INTERNAL and user.organization_id == deal.organization_id:
            return True

        # External users need explicit collaborator record
        if user.user_type == UserType.EXTERNAL:
            collaborator = (
                db.query(DealCollaborator)
                .filter(
                    DealCollaborator.deal_id == deal_id,
                    DealCollaborator.user_id == user.id,
                    DealCollaborator.is_active == "true"
                )
                .first()
            )
            return collaborator is not None

        return False

    @staticmethod
    def get_user_permissions(user: User, deal_id: UUID, db: Session) -> Dict[str, bool]:
        """
        Get granular permissions for a user on a specific deal.

        Returns dict like:
        {
            "can_view_docs": True,
            "can_comment": True,
            "can_upload_docs": False,
            "can_view_internal_reviews": False,
            "can_view_correspondence": True,
            "can_approve_drafts": False,
            "can_invite_others": False
        }
        """
        # Default permissions (most restrictive)
        permissions = {
            "can_view_docs": False,
            "can_comment": False,
            "can_upload_docs": False,
            "can_view_internal_reviews": False,
            "can_view_correspondence": False,
            "can_approve_drafts": False,
            "can_invite_others": False,
            "can_sign_contracts": False,
        }

        # Check if user can even access the deal
        if not PermissionService.can_access_deal(user, deal_id, db):
            return permissions

        # Internal users get full permissions on org deals
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if user.user_type == UserType.INTERNAL and user.organization_id == deal.organization_id:
            return {
                "can_view_docs": True,
                "can_comment": True,
                "can_upload_docs": True,
                "can_view_internal_reviews": True,
                "can_view_correspondence": True,
                "can_approve_drafts": True,
                "can_invite_others": True,
                "can_sign_contracts": True,
            }

        # External users: check collaborator permissions
        if user.user_type == UserType.EXTERNAL:
            collaborator = (
                db.query(DealCollaborator)
                .filter(
                    DealCollaborator.deal_id == deal_id,
                    DealCollaborator.user_id == user.id,
                    DealCollaborator.is_active == "true"
                )
                .first()
            )

            if collaborator:
                # Default external reviewer permissions
                permissions = {
                    "can_view_docs": True,
                    "can_comment": True,
                    "can_upload_docs": False,
                    "can_view_internal_reviews": False,  # Never see internal workflow
                    "can_view_correspondence": True,  # Can see correspondence involving them
                    "can_approve_drafts": False,  # External users don't approve
                    "can_invite_others": False,
                    "can_sign_contracts": collaborator.role == "external_signer",
                }

                # Override with custom permissions if set
                if collaborator.permissions:
                    permissions.update(collaborator.permissions)

        return permissions

    @staticmethod
    def filter_correspondence_for_user(
        user: User,
        deal_id: UUID,
        correspondence_list: list,
        db: Session
    ) -> list:
        """
        Filter correspondence based on user permissions.

        Internal users: See all correspondence
        External users: Only see correspondence where they're sender/recipient
        """
        # Internal users see everything
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if user.user_type == UserType.INTERNAL and user.organization_id == deal.organization_id:
            return correspondence_list

        # External users only see correspondence involving them
        if user.user_type == UserType.EXTERNAL:
            return [
                corr for corr in correspondence_list
                if user.email in [corr.sender, corr.recipient]
            ]

        return []

    @staticmethod
    def can_view_internal_reviews(user: User, deal_id: UUID, db: Session) -> bool:
        """Check if user can see internal review workflow"""
        permissions = PermissionService.get_user_permissions(user, deal_id, db)
        return permissions.get("can_view_internal_reviews", False)

    @staticmethod
    def record_deal_access(user: User, deal_id: UUID, db: Session) -> None:
        """
        Track when external users access a deal (for engagement metrics).
        Internal users are not tracked.
        """
        if user.user_type == UserType.EXTERNAL:
            collaborator = (
                db.query(DealCollaborator)
                .filter(
                    DealCollaborator.deal_id == deal_id,
                    DealCollaborator.user_id == user.id
                )
                .first()
            )

            if collaborator:
                from datetime import datetime
                collaborator.last_accessed_at = datetime.utcnow()

                # Increment access count
                try:
                    current_count = int(collaborator.access_count or "0")
                    collaborator.access_count = str(current_count + 1)
                except:
                    collaborator.access_count = "1"

                # Mark as accepted if first access
                if not collaborator.accepted_at:
                    collaborator.accepted_at = datetime.utcnow()

                db.commit()
