import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class Usuario(db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(255))
    rol = db.Column(db.String(50), default='operator')
    activo = db.Column(db.Boolean, default=True)
    ultimo_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'email', name='unique_tenant_email'),
    )

    # Relationships
    tenant = db.relationship('Tenant', back_populates='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'email': self.email,
            'nombre': self.nombre,
            'rol': self.rol,
            'activo': self.activo,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None,
            'created_at': self.created_at.isoformat()
        }
