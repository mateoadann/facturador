"""campos de personalizacion de email

Revision ID: 3db3c7604fba
Revises: f4684792aa2a
Create Date: 2026-02-12 18:55:09.245800
"""
from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists


revision = '3db3c7604fba'
down_revision = 'f4684792aa2a'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('email_config', 'email_asunto'):
        op.add_column('email_config', sa.Column('email_asunto', sa.String(length=500), nullable=True))
    if not column_exists('email_config', 'email_mensaje'):
        op.add_column('email_config', sa.Column('email_mensaje', sa.Text(), nullable=True))
    if not column_exists('email_config', 'email_saludo'):
        op.add_column('email_config', sa.Column('email_saludo', sa.String(length=500), nullable=True))


def downgrade():
    if column_exists('email_config', 'email_saludo'):
        op.drop_column('email_config', 'email_saludo')
    if column_exists('email_config', 'email_mensaje'):
        op.drop_column('email_config', 'email_mensaje')
    if column_exists('email_config', 'email_asunto'):
        op.drop_column('email_config', 'email_asunto')
