"""add_audit_fields_to_internal_reviews

Revision ID: a79fd0648d46
Revises: 45da203a5c50
Create Date: 2026-06-26 02:44:42.402889

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a79fd0648d46'
down_revision: Union[str, None] = '45da203a5c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audit and tracking fields to internal_reviews
    op.add_column('internal_reviews', sa.Column('draft_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('internal_reviews', sa.Column('previous_status', sa.String(), nullable=True))
    op.add_column('internal_reviews', sa.Column('new_status', sa.String(), nullable=False, server_default='internal_draft'))
    op.add_column('internal_reviews', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('internal_reviews', sa.Column('user_agent', sa.String(), nullable=True))
    op.add_column('internal_reviews', sa.Column('sent_to_party_name', sa.String(), nullable=True))
    op.add_column('internal_reviews', sa.Column('sent_to_party_email', sa.String(), nullable=True))

    # Create indexes for audit queries
    op.create_index('ix_internal_reviews_reviewer_id', 'internal_reviews', ['reviewer_id'])
    op.create_index('ix_internal_reviews_reviewee_id', 'internal_reviews', ['reviewee_id'])
    op.create_index('ix_internal_reviews_action', 'internal_reviews', ['action'])
    op.create_index('ix_internal_reviews_new_status', 'internal_reviews', ['new_status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_internal_reviews_new_status', table_name='internal_reviews')
    op.drop_index('ix_internal_reviews_action', table_name='internal_reviews')
    op.drop_index('ix_internal_reviews_reviewee_id', table_name='internal_reviews')
    op.drop_index('ix_internal_reviews_reviewer_id', table_name='internal_reviews')

    # Drop columns
    op.drop_column('internal_reviews', 'sent_to_party_email')
    op.drop_column('internal_reviews', 'sent_to_party_name')
    op.drop_column('internal_reviews', 'user_agent')
    op.drop_column('internal_reviews', 'ip_address')
    op.drop_column('internal_reviews', 'new_status')
    op.drop_column('internal_reviews', 'previous_status')
    op.drop_column('internal_reviews', 'draft_version')
