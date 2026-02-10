"""Initial migration - all tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Tenant
    op.create_table(
        'tenant',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # Usuario
    op.create_table(
        'usuario',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('nombre', sa.String(255)),
        sa.Column('rol', sa.String(50), server_default='operator'),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('ultimo_login', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email', name='unique_tenant_email'),
    )

    # Facturador
    op.create_table(
        'facturador',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id'), nullable=False),
        sa.Column('cuit', sa.String(13), nullable=False),
        sa.Column('razon_social', sa.String(255), nullable=False),
        sa.Column('direccion', sa.String(500)),
        sa.Column('condicion_iva', sa.String(100)),
        sa.Column('punto_venta', sa.Integer(), nullable=False),
        sa.Column('cert_encrypted', sa.LargeBinary()),
        sa.Column('key_encrypted', sa.LargeBinary()),
        sa.Column('ambiente', sa.String(20), server_default='testing'),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'cuit', 'punto_venta', name='unique_tenant_cuit_pv'),
    )

    # Receptor
    op.create_table(
        'receptor',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id'), nullable=False),
        sa.Column('doc_tipo', sa.Integer(), server_default='80'),
        sa.Column('doc_nro', sa.String(13), nullable=False),
        sa.Column('razon_social', sa.String(255), nullable=False),
        sa.Column('direccion', sa.String(500)),
        sa.Column('condicion_iva', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('activo', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'doc_nro', name='unique_tenant_doc_nro'),
    )

    # Lote
    op.create_table(
        'lote',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id'), nullable=False),
        sa.Column('etiqueta', sa.String(255)),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('estado', sa.String(50), server_default='pendiente'),
        sa.Column('total_facturas', sa.Integer(), server_default='0'),
        sa.Column('facturas_ok', sa.Integer(), server_default='0'),
        sa.Column('facturas_error', sa.Integer(), server_default='0'),
        sa.Column('celery_task_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Factura
    op.create_table(
        'factura',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id'), nullable=False),
        sa.Column('lote_id', sa.UUID(), sa.ForeignKey('lote.id')),
        sa.Column('facturador_id', sa.UUID(), sa.ForeignKey('facturador.id'), nullable=False),
        sa.Column('receptor_id', sa.UUID(), sa.ForeignKey('receptor.id'), nullable=False),
        sa.Column('tipo_comprobante', sa.Integer(), nullable=False),
        sa.Column('concepto', sa.Integer(), nullable=False),
        sa.Column('punto_venta', sa.Integer(), nullable=False),
        sa.Column('numero_comprobante', sa.BigInteger()),
        sa.Column('fecha_emision', sa.Date(), nullable=False),
        sa.Column('fecha_desde', sa.Date()),
        sa.Column('fecha_hasta', sa.Date()),
        sa.Column('fecha_vto_pago', sa.Date()),
        sa.Column('importe_total', sa.Numeric(15, 2), nullable=False),
        sa.Column('importe_neto', sa.Numeric(15, 2), nullable=False),
        sa.Column('importe_iva', sa.Numeric(15, 2), server_default='0'),
        sa.Column('moneda', sa.String(3), server_default="'PES'"),
        sa.Column('cotizacion', sa.Numeric(15, 6), server_default='1'),
        sa.Column('cae', sa.String(20)),
        sa.Column('cae_vencimiento', sa.Date()),
        sa.Column('estado', sa.String(50), server_default="'borrador'"),
        sa.Column('error_codigo', sa.String(50)),
        sa.Column('error_mensaje', sa.Text()),
        sa.Column('cbte_asoc_tipo', sa.Integer()),
        sa.Column('cbte_asoc_pto_vta', sa.Integer()),
        sa.Column('cbte_asoc_nro', sa.BigInteger()),
        sa.Column('arca_request', postgresql.JSON()),
        sa.Column('arca_response', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Factura Item
    op.create_table(
        'factura_item',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('factura_id', sa.UUID(), sa.ForeignKey('factura.id', ondelete='CASCADE'), nullable=False),
        sa.Column('descripcion', sa.String(500), nullable=False),
        sa.Column('cantidad', sa.Numeric(15, 4), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(15, 4), nullable=False),
        sa.Column('alicuota_iva_id', sa.Integer(), server_default='5'),
        sa.Column('importe_iva', sa.Numeric(15, 2), server_default='0'),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False),
        sa.Column('orden', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('factura_item')
    op.drop_table('factura')
    op.drop_table('lote')
    op.drop_table('receptor')
    op.drop_table('facturador')
    op.drop_table('usuario')
    op.drop_table('tenant')
