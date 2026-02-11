import json
from flask import request, g
from ..extensions import db
from ..models.auditoria import AuditLog


def log_action(accion, recurso=None, recurso_id=None, detalle=None):
    """Registrar una accion en el log de auditoria.

    No hace commit - se commitea con la transaccion principal.
    """
    tenant_id = getattr(g, 'tenant_id', None)
    current_user = getattr(g, 'current_user', None)

    log = AuditLog(
        tenant_id=tenant_id,
        usuario_id=current_user.id if current_user else None,
        accion=accion,
        recurso=recurso,
        recurso_id=str(recurso_id) if recurso_id else None,
        detalle=json.dumps(detalle) if detalle else None,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent', '')[:500] if request else None,
    )
    db.session.add(log)
