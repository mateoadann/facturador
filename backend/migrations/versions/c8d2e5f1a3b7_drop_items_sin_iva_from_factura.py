"""drop items_sin_iva from factura

Revision ID: c8d2e5f1a3b7
Revises: a7e1f3c9d4b2
Create Date: 2026-03-24 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d2e5f1a3b7'
down_revision = 'a7e1f3c9d4b2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('factura', 'items_sin_iva')


def downgrade():
    op.add_column('factura', sa.Column('items_sin_iva', sa.Boolean(), nullable=True, server_default=sa.text('false')))
