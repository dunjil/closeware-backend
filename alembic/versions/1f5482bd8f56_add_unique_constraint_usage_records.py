"""add_unique_constraint_usage_records

Revision ID: 1f5482bd8f56
Revises: c9d5eeff0560
Create Date: 2026-06-26 11:04:45.932663

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '1f5482bd8f56'
down_revision: Union[str, None] = 'c9d5eeff0560'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint: one CONTRACT_GENERATION usage per organization+deal
    # This prevents double-counting when two users generate simultaneously
    op.create_unique_constraint(
        'uq_usage_record_org_deal_generation',
        'usage_records',
        ['organization_id', 'deal_id', 'usage_type']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_usage_record_org_deal_generation',
        'usage_records',
        type_='unique'
    )
