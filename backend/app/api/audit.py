from flask import Blueprint, request, jsonify, g
from ..models.auditoria import AuditLog
from ..utils import permission_required

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('', methods=['GET'])
@permission_required('auditoria:ver')
def list_audit_logs():
    """Listar logs de auditoría del tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    usuario_id = request.args.get('usuario_id')
    accion = request.args.get('accion')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')

    query = AuditLog.query.filter_by(tenant_id=g.tenant_id)

    if usuario_id:
        query = query.filter_by(usuario_id=usuario_id)
    if accion:
        query = query.filter(AuditLog.accion.ilike(f'%{accion}%'))
    if fecha_desde:
        query = query.filter(AuditLog.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.filter(AuditLog.created_at <= fecha_hasta)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200
