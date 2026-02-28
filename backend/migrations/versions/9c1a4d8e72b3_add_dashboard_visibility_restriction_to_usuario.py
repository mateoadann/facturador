"""add dashboard visibility restriction to usuario

Revision ID: 9c1a4d8e72b3
Revises: 6f2c9c2b1c41
Create Date: 2026-02-28 14:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists


revision = '9c1a4d8e72b3'
down_revision = '6f2c9c2b1c41'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('usuario', 'restringir_dashboard_sensible'):
        op.add_column(
            'usuario',
            sa.Column('restringir_dashboard_sensible', sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade():
    if column_exists('usuario', 'restringir_dashboard_sensible'):
        op.drop_column('usuario', 'restringir_dashboard_sensible')
