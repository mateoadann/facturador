import uuid
from datetime import datetime
from ..extensions import db


class Tenant(db.Model):
    __tablename__ = 'tenant'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    usuarios = db.relationship('Usuario', back_populates='tenant', lazy='dynamic')
    facturadores = db.relationship('Facturador', back_populates='tenant', lazy='dynamic')
    receptores = db.relationship('Receptor', back_populates='tenant', lazy='dynamic')
    lotes = db.relationship('Lote', back_populates='tenant', lazy='dynamic')
    facturas = db.relationship('Factura', back_populates='tenant', lazy='dynamic')

    def to_dict(self):
        return {
            'id': str(self.id),
            'nombre': self.nombre,
            'slug': self.slug,
            'activo': self.activo,
            'created_at': self.created_at.isoformat()
        }
