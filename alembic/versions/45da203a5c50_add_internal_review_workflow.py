"""add_internal_review_workflow

Revision ID: 45da203a5c50
Revises: add_signatures_table
Create Date: 2026-06-26 02:32:38.430366

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '45da203a5c50'
down_revision: Union[str, None] = 'add_signatures_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add workflow tracking columns to contract_drafts
    op.add_column('contract_drafts', sa.Column('status', sa.String(), nullable=False, server_default='internal_draft'))
    op.add_column('contract_drafts', sa.Column('current_reviewer_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('contract_drafts', sa.Column('sent_externally_at', sa.DateTime(), nullable=True))
    op.add_column('contract_drafts', sa.Column('sent_to_party', sa.String(), nullable=True))

    # Add foreign key for current_reviewer_id
    op.create_foreign_key(
        'fk_contract_drafts_current_reviewer_id',
        'contract_drafts', 'users',
        ['current_reviewer_id'], ['id']
    )

    # Create internal_reviews table
    op.create_table(
        'internal_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_draft_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['contract_draft_id'], ['contract_drafts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewee_id'], ['users.id']),
    )

    # Create indexes
    op.create_index('ix_internal_reviews_contract_draft_id', 'internal_reviews', ['contract_draft_id'])
    op.create_index('ix_internal_reviews_deal_id', 'internal_reviews', ['deal_id'])
    op.create_index('ix_contract_drafts_status', 'contract_drafts', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_contract_drafts_status', table_name='contract_drafts')
    op.drop_index('ix_internal_reviews_deal_id', table_name='internal_reviews')
    op.drop_index('ix_internal_reviews_contract_draft_id', table_name='internal_reviews')

    # Drop internal_reviews table
    op.drop_table('internal_reviews')

    # Drop foreign key and columns from contract_drafts
    op.drop_constraint('fk_contract_drafts_current_reviewer_id', 'contract_drafts', type_='foreignkey')
    op.drop_column('contract_drafts', 'sent_to_party')
    op.drop_column('contract_drafts', 'sent_externally_at')
    op.drop_column('contract_drafts', 'current_reviewer_id')
    op.drop_column('contract_drafts', 'status')
