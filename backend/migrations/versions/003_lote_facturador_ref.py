"""Add facturador reference to lote

Revision ID: 003_lote_fact_ref
Revises: 002_fact_ambiente
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa
from migrations.helpers import column_exists, fk_exists


revision = '003_lote_fact_ref'
down_revision = '002_fact_ambiente'
branch_labels = None
depends_on = None


def upgrade():
    if not column_exists('lote', 'facturador_id'):
        op.add_column('lote', sa.Column('facturador_id', sa.UUID(), nullable=True))

    if not fk_exists('lote', 'fk_lote_facturador_id'):
        op.create_foreign_key(
            'fk_lote_facturador_id',
            'lote',
            'facturador',
            ['facturador_id'],
            ['id']
        )

    op.execute(
        """
        UPDATE lote l
        SET facturador_id = s.facturador_id
        FROM (
            SELECT lote_id, MIN(facturador_id::text)::uuid AS facturador_id
            FROM factura
            WHERE lote_id IS NOT NULL
            GROUP BY lote_id
            HAVING COUNT(DISTINCT facturador_id) = 1
        ) s
        WHERE l.id = s.lote_id AND l.facturador_id IS NULL
        """
    )


def downgrade():
    if fk_exists('lote', 'fk_lote_facturador_id'):
        op.drop_constraint('fk_lote_facturador_id', 'lote', type_='foreignkey')
    if column_exists('lote', 'facturador_id'):
        op.drop_column('lote', 'facturador_id')
