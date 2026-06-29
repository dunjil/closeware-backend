"""add_signature_workflow_and_requests

Revision ID: 2641c7dc4860
Revises: 1f5482bd8f56
Create Date: 2026-06-26 14:39:40.750948

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2641c7dc4860'
down_revision: Union[str, None] = '1f5482bd8f56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new statuses to DraftStatus enum
    op.execute("""
        ALTER TYPE draftstatus ADD VALUE IF NOT EXISTS 'ready_for_signing';
        ALTER TYPE draftstatus ADD VALUE IF NOT EXISTS 'awaiting_signatures';
        ALTER TYPE draftstatus ADD VALUE IF NOT EXISTS 'partially_signed';
        ALTER TYPE draftstatus ADD VALUE IF NOT EXISTS 'fully_executed';
    """)

    # Create SignatureRole enum
    op.execute("""
        CREATE TYPE signaturerole AS ENUM ('buyer', 'seller', 'witness', 'guarantor', 'other');
    """)

    # Create SignatureRequestStatus enum
    op.execute("""
        CREATE TYPE signaturerequeststatus AS ENUM ('pending', 'signed', 'declined', 'expired');
    """)

    # Create signature_requests table
    op.create_table(
        'signature_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_draft_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contract_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('signer_name', sa.String(), nullable=False),
        sa.Column('signer_email', sa.String(), nullable=False),
        sa.Column('signer_title', sa.String(), nullable=True),
        sa.Column('signer_role', postgresql.ENUM('buyer', 'seller', 'witness', 'guarantor', 'other', name='signaturerole'), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'signed', 'declined', 'expired', name='signaturerequeststatus'), nullable=False),
        sa.Column('request_message', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=False, unique=True),
        sa.Column('requested_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('signature_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('signatures.id'), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('declined_at', sa.DateTime(), nullable=True),
        sa.Column('decline_reason', sa.String(), nullable=True)
    )

    # Create indexes
    op.create_index('ix_signature_requests_contract_draft_id', 'signature_requests', ['contract_draft_id'])
    op.create_index('ix_signature_requests_signer_email', 'signature_requests', ['signer_email'])
    op.create_index('ix_signature_requests_status', 'signature_requests', ['status'])
    op.create_index('ix_signature_requests_access_token', 'signature_requests', ['access_token'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_signature_requests_access_token', 'signature_requests')
    op.drop_index('ix_signature_requests_status', 'signature_requests')
    op.drop_index('ix_signature_requests_signer_email', 'signature_requests')
    op.drop_index('ix_signature_requests_contract_draft_id', 'signature_requests')

    # Drop table
    op.drop_table('signature_requests')

    # Drop enums
    op.execute('DROP TYPE signaturerequeststatus')
    op.execute('DROP TYPE signaturerole')

    # Note: Cannot easily remove enum values from draftstatus, so we leave them
