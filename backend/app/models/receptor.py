import uuid
from datetime import datetime
from ..extensions import db


class Receptor(db.Model):
    __tablename__ = 'receptor'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    doc_tipo = db.Column(db.Integer, default=80)  # 80 = CUIT
    doc_nro = db.Column(db.String(13), nullable=False)
    razon_social = db.Column(db.String(255), nullable=False)
    direccion = db.Column(db.String(500))
    condicion_iva = db.Column(db.String(100))
    email = db.Column(db.String(255))
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'doc_nro', name='unique_tenant_doc_nro'),
    )

    # Relationships
    tenant = db.relationship('Tenant', back_populates='receptores')
    facturas = db.relationship('Factura', back_populates='receptor', lazy='dynamic')

    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'doc_tipo': self.doc_tipo,
            'doc_nro': self.doc_nro,
            'razon_social': self.razon_social,
            'direccion': self.direccion,
            'condicion_iva': self.condicion_iva,
            'email': self.email,
            'activo': self.activo,
            'created_at': self.created_at.isoformat()
        }
