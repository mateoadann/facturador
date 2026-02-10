import uuid
from datetime import datetime
from decimal import Decimal
from ..extensions import db


class Factura(db.Model):
    __tablename__ = 'factura'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    lote_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('lote.id'))
    facturador_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('facturador.id'), nullable=False)
    receptor_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('receptor.id'), nullable=False)

    # Datos del comprobante
    tipo_comprobante = db.Column(db.Integer, nullable=False)  # 1=FC A, 6=FC B, 11=FC C, etc.
    concepto = db.Column(db.Integer, nullable=False)  # 1=Productos, 2=Servicios, 3=Ambos
    punto_venta = db.Column(db.Integer, nullable=False)
    numero_comprobante = db.Column(db.BigInteger)

    # Fechas
    fecha_emision = db.Column(db.Date, nullable=False)
    fecha_desde = db.Column(db.Date)
    fecha_hasta = db.Column(db.Date)
    fecha_vto_pago = db.Column(db.Date)

    # Importes
    importe_total = db.Column(db.Numeric(15, 2), nullable=False)
    importe_neto = db.Column(db.Numeric(15, 2), nullable=False)
    importe_iva = db.Column(db.Numeric(15, 2), default=Decimal('0'))

    # Moneda
    moneda = db.Column(db.String(3), default='PES')
    cotizacion = db.Column(db.Numeric(15, 6), default=Decimal('1'))

    # CAE
    cae = db.Column(db.String(20))
    cae_vencimiento = db.Column(db.Date)

    # Estado
    estado = db.Column(db.String(50), default='borrador')  # 'borrador', 'pendiente', 'autorizado', 'error'
    error_codigo = db.Column(db.String(50))
    error_mensaje = db.Column(db.Text)

    # Comprobante asociado (para notas de crédito/débito)
    cbte_asoc_tipo = db.Column(db.Integer)
    cbte_asoc_pto_vta = db.Column(db.Integer)
    cbte_asoc_nro = db.Column(db.BigInteger)

    # ARCA request/response
    arca_request = db.Column(db.JSON)
    arca_response = db.Column(db.JSON)

    # Comprobante renderizado (HTML). El PDF se genera on-demand.
    comprobante_html = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tenant = db.relationship('Tenant', back_populates='facturas')
    lote = db.relationship('Lote', back_populates='facturas')
    facturador = db.relationship('Facturador', back_populates='facturas')
    receptor = db.relationship('Receptor', back_populates='facturas')
    items = db.relationship('FacturaItem', back_populates='factura', cascade='all, delete-orphan')

    def to_dict(self, include_items=False):
        data = {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'lote_id': str(self.lote_id) if self.lote_id else None,
            'facturador_id': str(self.facturador_id),
            'receptor_id': str(self.receptor_id),
            'tipo_comprobante': self.tipo_comprobante,
            'concepto': self.concepto,
            'punto_venta': self.punto_venta,
            'numero_comprobante': self.numero_comprobante,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'fecha_desde': self.fecha_desde.isoformat() if self.fecha_desde else None,
            'fecha_hasta': self.fecha_hasta.isoformat() if self.fecha_hasta else None,
            'fecha_vto_pago': self.fecha_vto_pago.isoformat() if self.fecha_vto_pago else None,
            'importe_total': float(self.importe_total),
            'importe_neto': float(self.importe_neto),
            'importe_iva': float(self.importe_iva) if self.importe_iva else 0,
            'moneda': self.moneda,
            'cotizacion': float(self.cotizacion) if self.cotizacion else 1,
            'cae': self.cae,
            'cae_vencimiento': self.cae_vencimiento.isoformat() if self.cae_vencimiento else None,
            'estado': self.estado,
            'error_codigo': self.error_codigo,
            'error_mensaje': self.error_mensaje,
            'cbte_asoc_tipo': self.cbte_asoc_tipo,
            'cbte_asoc_pto_vta': self.cbte_asoc_pto_vta,
            'cbte_asoc_nro': self.cbte_asoc_nro,
            'tiene_comprobante_html': bool(self.comprobante_html),
            'created_at': self.created_at.isoformat(),
            'facturador': self.facturador.to_dict() if self.facturador else None,
            'receptor': self.receptor.to_dict() if self.receptor else None,
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        return data


class FacturaItem(db.Model):
    __tablename__ = 'factura_item'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factura_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('factura.id', ondelete='CASCADE'), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    cantidad = db.Column(db.Numeric(15, 4), nullable=False)
    precio_unitario = db.Column(db.Numeric(15, 4), nullable=False)
    alicuota_iva_id = db.Column(db.Integer, default=5)  # 5 = 21%
    importe_iva = db.Column(db.Numeric(15, 2), default=Decimal('0'))
    subtotal = db.Column(db.Numeric(15, 2), nullable=False)
    orden = db.Column(db.Integer, default=0)

    # Relationships
    factura = db.relationship('Factura', back_populates='items')

    def to_dict(self):
        return {
            'id': str(self.id),
            'factura_id': str(self.factura_id),
            'descripcion': self.descripcion,
            'cantidad': float(self.cantidad),
            'precio_unitario': float(self.precio_unitario),
            'alicuota_iva_id': self.alicuota_iva_id,
            'importe_iva': float(self.importe_iva) if self.importe_iva else 0,
            'subtotal': float(self.subtotal),
            'orden': self.orden
        }
