"""add_contract_status_history_and_features

Revision ID: 3a45f7bc9e12
Revises: 2641c7dc4860
Create Date: 2026-07-03 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3a45f7bc9e12'
down_revision: Union[str, None] = '2641c7dc4860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create contract_status_history table
    op.create_table(
        'contract_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_draft_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contract_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_status', sa.String(), nullable=True),
        sa.Column('new_status', sa.String(), nullable=False),
        sa.Column('changed_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True)
    )

    # Create indexes for performance
    op.create_index('ix_contract_status_history_contract_draft_id', 'contract_status_history', ['contract_draft_id'])
    op.create_index('ix_contract_status_history_changed_at', 'contract_status_history', ['changed_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_contract_status_history_changed_at', 'contract_status_history')
    op.drop_index('ix_contract_status_history_contract_draft_id', 'contract_status_history')

    # Drop table
    op.drop_table('contract_status_history')
