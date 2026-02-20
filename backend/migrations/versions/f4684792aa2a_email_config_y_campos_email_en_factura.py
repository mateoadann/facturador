"""email_config y campos email en factura

Revision ID: f4684792aa2a
Revises: 004_fact_html
Create Date: 2026-02-11 18:25:53.822927
"""
from alembic import op
import sqlalchemy as sa
from migrations.helpers import table_exists, column_exists


revision = 'f4684792aa2a'
down_revision = '004_fact_html'
branch_labels = None
depends_on = None


def upgrade():
    if not table_exists('email_config'):
        op.create_table('email_config',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('smtp_host', sa.String(length=255), nullable=False),
        sa.Column('smtp_port', sa.Integer(), nullable=True),
        sa.Column('smtp_use_tls', sa.Boolean(), nullable=True),
        sa.Column('smtp_user', sa.String(length=255), nullable=False),
        sa.Column('smtp_password_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('from_email', sa.String(length=255), nullable=False),
        sa.Column('from_name', sa.String(length=255), nullable=True),
        sa.Column('email_habilitado', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
        )

    if not column_exists('factura', 'email_enviado'):
        op.add_column('factura', sa.Column('email_enviado', sa.Boolean(), nullable=True))
    if not column_exists('factura', 'email_enviado_at'):
        op.add_column('factura', sa.Column('email_enviado_at', sa.DateTime(), nullable=True))
    if not column_exists('factura', 'email_error'):
        op.add_column('factura', sa.Column('email_error', sa.String(length=500), nullable=True))


def downgrade():
    if column_exists('factura', 'email_error'):
        op.drop_column('factura', 'email_error')
    if column_exists('factura', 'email_enviado_at'):
        op.drop_column('factura', 'email_enviado_at')
    if column_exists('factura', 'email_enviado'):
        op.drop_column('factura', 'email_enviado')
    if table_exists('email_config'):
        op.drop_table('email_config')
