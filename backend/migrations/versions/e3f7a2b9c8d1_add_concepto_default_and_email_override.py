"""add concepto_default to facturador and email_override to factura

Revision ID: e3f7a2b9c8d1
Revises: d5a8f2e7c1b9
Create Date: 2026-04-23 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e3f7a2b9c8d1'
down_revision = 'd5a8f2e7c1b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('facturador', sa.Column('concepto_default', sa.Integer(), nullable=True))
    op.add_column('factura', sa.Column('email_override', sa.String(1000), nullable=True))


def downgrade():
    op.drop_column('factura', 'email_override')
    op.drop_column('facturador', 'concepto_default')
