"""add_verification_tokens_table

Revision ID: c9d5eeff0560
Revises: e8233be2e2be
Create Date: 2026-06-26 11:04:25.805218

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c9d5eeff0560'
down_revision: Union[str, None] = 'e8233be2e2be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create token_type enum using raw SQL (avoid SQLAlchemy's auto-create)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tokentype AS ENUM ('email_verification', 'password_reset');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create verification_tokens table using raw SQL to avoid enum auto-creation
    op.execute("""
        CREATE TABLE verification_tokens (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            token VARCHAR NOT NULL UNIQUE,
            token_type tokentype NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now()
        )
    """)

    # Create indexes for common queries
    op.create_index('ix_verification_tokens_user_id', 'verification_tokens', ['user_id'])
    op.create_index('ix_verification_tokens_token_type', 'verification_tokens', ['token_type'])


def downgrade() -> None:
    op.drop_index('ix_verification_tokens_token_type', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_user_id', table_name='verification_tokens')
    op.drop_table('verification_tokens')
    op.execute('DROP TYPE tokentype')
