import uuid
from datetime import datetime
from ..extensions import db


class Facturador(db.Model):
    __tablename__ = 'facturador'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    cuit = db.Column(db.String(13), nullable=False)
    razon_social = db.Column(db.String(255), nullable=False)
    direccion = db.Column(db.String(500))
    condicion_iva = db.Column(db.String(100))
    punto_venta = db.Column(db.Integer, nullable=False)
    cert_encrypted = db.Column(db.LargeBinary)
    key_encrypted = db.Column(db.LargeBinary)
    ambiente = db.Column(db.String(20), default='testing')
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'cuit', 'punto_venta', 'ambiente', name='unique_tenant_cuit_pv_ambiente'),
    )

    # Relationships
    tenant = db.relationship('Tenant', back_populates='facturadores')
    facturas = db.relationship('Factura', back_populates='facturador', lazy='dynamic')
    lotes = db.relationship('Lote', back_populates='facturador', lazy='dynamic')

    def to_dict(self, include_certs=False):
        data = {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'cuit': self.cuit,
            'razon_social': self.razon_social,
            'direccion': self.direccion,
            'condicion_iva': self.condicion_iva,
            'punto_venta': self.punto_venta,
            'ambiente': self.ambiente,
            'activo': self.activo,
            'tiene_certificados': self.cert_encrypted is not None and self.key_encrypted is not None,
            'created_at': self.created_at.isoformat()
        }
        return data
