"""add_external_user_and_collaborator_system

Revision ID: 82b964635d39
Revises: a79fd0648d46
Create Date: 2026-06-26 02:57:01.813372

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '82b964635d39'
down_revision: Union[str, None] = 'a79fd0648d46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table for external user support
    op.add_column('users', sa.Column('user_type', sa.String(), nullable=False, server_default='internal'))
    op.add_column('users', sa.Column('external_organization_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('users', sa.Column('title', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))

    # Make organization_id and role nullable for external users
    op.alter_column('users', 'organization_id', nullable=True)
    op.alter_column('users', 'role', nullable=True)

    # Add 'owner' to UserRole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'owner'")

    # Create deal_collaborators table
    op.create_table(
        'deal_collaborators',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('permissions', postgresql.JSONB(), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.String(), nullable=True),
        sa.Column('is_active', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id']),
    )
    op.create_index('ix_deal_collaborators_deal_id', 'deal_collaborators', ['deal_id'])
    op.create_index('ix_deal_collaborators_user_id', 'deal_collaborators', ['user_id'])

    # Create pending_external_users table
    op.create_table(
        'pending_external_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('organization_name', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('invited_to_deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invite_token', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message', sa.String(), nullable=True),
        sa.Column('collaborator_role', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('created_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invited_to_deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_user_id'], ['users.id']),
    )
    op.create_index('ix_pending_external_users_email', 'pending_external_users', ['email'])
    op.create_index('ix_pending_external_users_deal_id', 'pending_external_users', ['invited_to_deal_id'])
    op.create_index('ix_pending_external_users_token', 'pending_external_users', ['invite_token'], unique=True)


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_pending_external_users_token', table_name='pending_external_users')
    op.drop_index('ix_pending_external_users_deal_id', table_name='pending_external_users')
    op.drop_index('ix_pending_external_users_email', table_name='pending_external_users')
    op.drop_table('pending_external_users')

    op.drop_index('ix_deal_collaborators_user_id', table_name='deal_collaborators')
    op.drop_index('ix_deal_collaborators_deal_id', table_name='deal_collaborators')
    op.drop_table('deal_collaborators')

    # Remove columns from users table
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'title')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'external_organization_name')
    op.drop_column('users', 'user_type')

    # Restore not null constraints
    op.alter_column('users', 'role', nullable=False)
    op.alter_column('users', 'organization_id', nullable=False)
