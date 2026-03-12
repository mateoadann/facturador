"""add ingresos_brutos and fecha_inicio_actividades to facturador

Revision ID: a1b2c3d4e5f6
Revises: 9c1a4d8e72b3
Create Date: 2026-03-12 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists


revision = 'a1b2c3d4e5f6'
down_revision = '9c1a4d8e72b3'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('facturador', 'ingresos_brutos'):
        op.add_column(
            'facturador',
            sa.Column('ingresos_brutos', sa.String(50), nullable=True),
        )
    if not column_exists('facturador', 'fecha_inicio_actividades'):
        op.add_column(
            'facturador',
            sa.Column('fecha_inicio_actividades', sa.Date(), nullable=True),
        )


def downgrade():
    if column_exists('facturador', 'fecha_inicio_actividades'):
        op.drop_column('facturador', 'fecha_inicio_actividades')
    if column_exists('facturador', 'ingresos_brutos'):
        op.drop_column('facturador', 'ingresos_brutos')
