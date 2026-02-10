"""Add comprobante_html field to factura

Revision ID: 004_fact_html
Revises: 003_lote_fact_ref
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa


revision = '004_fact_html'
down_revision = '003_lote_fact_ref'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('factura', sa.Column('comprobante_html', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('factura', 'comprobante_html')
