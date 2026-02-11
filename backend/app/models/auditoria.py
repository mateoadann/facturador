import uuid
from datetime import datetime
from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('tenant.id'), nullable=False)
    usuario_id = db.Column(db.Uuid(as_uuid=True), db.ForeignKey('usuario.id'), nullable=True)
    accion = db.Column(db.String(100), nullable=False)
    recurso = db.Column(db.String(100))
    recurso_id = db.Column(db.String(36))
    detalle = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_audit_log_tenant_created', 'tenant_id', 'created_at'),
        db.Index('ix_audit_log_usuario', 'usuario_id'),
    )

    tenant = db.relationship('Tenant')
    usuario = db.relationship('Usuario')

    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'usuario_id': str(self.usuario_id) if self.usuario_id else None,
            'usuario_nombre': self.usuario.nombre if self.usuario else None,
            'usuario_email': self.usuario.email if self.usuario else None,
            'accion': self.accion,
            'recurso': self.recurso,
            'recurso_id': self.recurso_id,
            'detalle': self.detalle,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }
