import uuid
from datetime import datetime
from ..extensions import db


class Lote(db.Model):
    __tablename__ = 'lote'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    facturador_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('facturador.id'))
    etiqueta = db.Column(db.String(255))
    tipo = db.Column(db.String(50), nullable=False)  # 'factura', 'nota_credito', 'nota_debito'
    estado = db.Column(db.String(50), default='pendiente')  # 'pendiente', 'procesando', 'completado', 'error'
    total_facturas = db.Column(db.Integer, default=0)
    facturas_ok = db.Column(db.Integer, default=0)
    facturas_error = db.Column(db.Integer, default=0)
    celery_task_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

    # Relationships
    tenant = db.relationship('Tenant', back_populates='lotes')
    facturador = db.relationship('Facturador', back_populates='lotes')
    facturas = db.relationship('Factura', back_populates='lote', lazy='dynamic')

    def to_dict(self, include_facturas=False):
        data = {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'facturador_id': str(self.facturador_id) if self.facturador_id else None,
            'etiqueta': self.etiqueta,
            'tipo': self.tipo,
            'estado': self.estado,
            'total_facturas': self.total_facturas,
            'facturas_ok': self.facturas_ok,
            'facturas_error': self.facturas_error,
            'celery_task_id': self.celery_task_id,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
        if self.facturador:
            data['facturador'] = {
                'id': str(self.facturador.id),
                'cuit': self.facturador.cuit,
                'razon_social': self.facturador.razon_social,
                'punto_venta': self.facturador.punto_venta,
                'ambiente': self.facturador.ambiente,
            }
        if include_facturas:
            data['facturas'] = [f.to_dict() for f in self.facturas]
        return data
