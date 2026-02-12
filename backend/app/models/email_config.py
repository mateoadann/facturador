import uuid
from datetime import datetime
from ..extensions import db


class EmailConfig(db.Model):
    __tablename__ = 'email_config'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), unique=True, nullable=False)

    smtp_host = db.Column(db.String(255), nullable=False)
    smtp_port = db.Column(db.Integer, default=587)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    smtp_user = db.Column(db.String(255), nullable=False)
    smtp_password_encrypted = db.Column(db.LargeBinary, nullable=False)
    from_email = db.Column(db.String(255), nullable=False)
    from_name = db.Column(db.String(255))

    email_habilitado = db.Column(db.Boolean, default=True)

    # Personalización del email
    email_asunto = db.Column(db.String(500))
    email_mensaje = db.Column(db.Text)
    email_saludo = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    tenant = db.relationship('Tenant', backref=db.backref('email_config', uselist=False))

    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'smtp_use_tls': self.smtp_use_tls,
            'smtp_user': self.smtp_user,
            'tiene_password': bool(self.smtp_password_encrypted),
            'from_email': self.from_email,
            'from_name': self.from_name,
            'email_habilitado': self.email_habilitado,
            'email_asunto': self.email_asunto,
            'email_mensaje': self.email_mensaje,
            'email_saludo': self.email_saludo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
