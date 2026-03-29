"""add email override fields to factura

Revision ID: d5a8f2e7c1b9
Revises: c8d2e5f1a3b7
Create Date: 2026-03-28 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd5a8f2e7c1b9'
down_revision = 'c8d2e5f1a3b7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('factura', sa.Column('emails_cc', sa.String(1000), nullable=True))
    op.add_column('factura', sa.Column('email_asunto', sa.String(500), nullable=True))
    op.add_column('factura', sa.Column('email_mensaje', sa.Text(), nullable=True))
    op.add_column('factura', sa.Column('email_firma', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('factura', 'email_firma')
    op.drop_column('factura', 'email_mensaje')
    op.drop_column('factura', 'email_asunto')
    op.drop_column('factura', 'emails_cc')
