"""Allow same CUIT/PV across environments for facturador

Revision ID: 002_fact_ambiente
Revises: 001_initial
Create Date: 2026-02-09
"""

from alembic import op


revision = '002_fact_ambiente'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('unique_tenant_cuit_pv', 'facturador', type_='unique')
    op.create_unique_constraint(
        'unique_tenant_cuit_pv_ambiente',
        'facturador',
        ['tenant_id', 'cuit', 'punto_venta', 'ambiente']
    )


def downgrade():
    op.drop_constraint('unique_tenant_cuit_pv_ambiente', 'facturador', type_='unique')
    op.create_unique_constraint(
        'unique_tenant_cuit_pv',
        'facturador',
        ['tenant_id', 'cuit', 'punto_venta']
    )
