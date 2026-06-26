"""add suggested_fix to discrepancy_items

Revision ID: a1b2c3d4e5f6
Revises: 503e57cef937
Create Date: 2026-06-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '503e57cef937'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('discrepancy_items', sa.Column('suggested_fix', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('discrepancy_items', 'suggested_fix')
