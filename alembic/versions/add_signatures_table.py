"""add signatures table

Revision ID: add_signatures_table
Revises: add_suggested_fix_to_discrepancy_items
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_signatures_table'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'signatures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_draft_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signer_name', sa.String(), nullable=False),
        sa.Column('signer_title', sa.String(), nullable=False),
        sa.Column('signer_email', sa.String(), nullable=True),
        sa.Column('signature_data', sa.Text(), nullable=False),
        sa.Column('signature_type', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=False),
        sa.Column('is_buyer', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['contract_draft_id'], ['contract_drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('signatures')
