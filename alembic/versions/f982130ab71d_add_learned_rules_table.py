"""add learned_rules table

Revision ID: f982130ab71d
Revises: e87401803cb0
Create Date: 2026-08-31 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f982130ab71d'
down_revision: Union[str, None] = 'e87401803cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('learned_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vendor', sa.String(), nullable=False),
    sa.Column('raw_pattern', sa.Text(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('field', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('created_by', sa.String(), nullable=False, server_default='admin'),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('learned_rules')
