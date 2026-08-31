"""add findings table

Revision ID: b28f731c9e42
Revises: f982130ab71d
Create Date: 2026-09-01 00:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b28f731c9e42'
down_revision: Union[str, None] = 'f982130ab71d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('findings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('rule_id', sa.String(), nullable=False),
    sa.Column('framework', sa.String(), nullable=False, server_default='CIS'),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('severity', sa.String(), nullable=False),
    sa.Column('remediation_text', sa.Text(), nullable=True),
    sa.Column('evaluated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('findings')
