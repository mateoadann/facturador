"""add ingresos brutos and inicio actividades to facturador

Revision ID: 1c3f9b2a4d10
Revises: 4156f1aef878
Create Date: 2026-03-12 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists


revision = '1c3f9b2a4d10'
down_revision = '4156f1aef878'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('facturador', 'ingresos_brutos'):
        op.add_column('facturador', sa.Column('ingresos_brutos', sa.String(length=50), nullable=True))

    if not column_exists('facturador', 'fecha_inicio_actividades'):
        op.add_column('facturador', sa.Column('fecha_inicio_actividades', sa.Date(), nullable=True))


def downgrade():
    if column_exists('facturador', 'fecha_inicio_actividades'):
        op.drop_column('facturador', 'fecha_inicio_actividades')

    if column_exists('facturador', 'ingresos_brutos'):
        op.drop_column('facturador', 'ingresos_brutos')
