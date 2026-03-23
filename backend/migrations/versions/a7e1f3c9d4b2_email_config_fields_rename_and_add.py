"""email config fields: rename email_saludo to email_despedida, add email_saludo and email_firma

Revision ID: a7e1f3c9d4b2
Revises: 906f4dd4b828
Create Date: 2026-03-23 23:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists


revision = 'a7e1f3c9d4b2'
down_revision = '906f4dd4b828'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Rename email_saludo -> email_despedida (preserves existing farewell data)
    if column_exists('email_config', 'email_saludo') and not column_exists('email_config', 'email_despedida'):
        op.alter_column('email_config', 'email_saludo', new_column_name='email_despedida')

    # Step 2: Add new email_saludo column (greeting, different purpose than the renamed one)
    if not column_exists('email_config', 'email_saludo'):
        op.add_column('email_config', sa.Column('email_saludo', sa.String(length=500), nullable=True))

    # Step 3: Add email_firma column (signature)
    if not column_exists('email_config', 'email_firma'):
        op.add_column('email_config', sa.Column('email_firma', sa.Text(), nullable=True))


def downgrade():
    # Remove new columns first
    if column_exists('email_config', 'email_firma'):
        op.drop_column('email_config', 'email_firma')

    if column_exists('email_config', 'email_saludo'):
        op.drop_column('email_config', 'email_saludo')

    # Rename email_despedida back to email_saludo
    if column_exists('email_config', 'email_despedida') and not column_exists('email_config', 'email_saludo'):
        op.alter_column('email_config', 'email_despedida', new_column_name='email_saludo')
