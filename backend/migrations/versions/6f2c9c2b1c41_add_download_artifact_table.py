"""add download artifact table

Revision ID: 6f2c9c2b1c41
Revises: 3db3c7604fba
Create Date: 2026-02-27 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from migrations.helpers import table_exists


revision = '6f2c9c2b1c41'
down_revision = '3db3c7604fba'
branch_labels = None
depends_on = None


def upgrade():
    if table_exists('download_artifact'):
        return

    op.create_table(
        'download_artifact',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id'),
    )
    op.create_index(op.f('ix_download_artifact_task_id'), 'download_artifact', ['task_id'], unique=True)
    op.create_index(op.f('ix_download_artifact_tenant_id'), 'download_artifact', ['tenant_id'], unique=False)


def downgrade():
    if not table_exists('download_artifact'):
        return

    op.drop_index(op.f('ix_download_artifact_tenant_id'), table_name='download_artifact')
    op.drop_index(op.f('ix_download_artifact_task_id'), table_name='download_artifact')
    op.drop_table('download_artifact')
