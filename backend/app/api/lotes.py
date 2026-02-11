from flask import Blueprint, request, jsonify, g
from uuid import UUID
from ..extensions import db
from ..models import Lote, Factura, Facturador
from ..utils import permission_required
from ..services.audit import log_action

lotes_bp = Blueprint('lotes', __name__)


@lotes_bp.route('', methods=['GET'])
@permission_required('facturas:ver')
def list_lotes():
    """Listar lotes del tenant."""
    _purge_empty_lotes(g.tenant_id)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')

    query = Lote.query.filter_by(tenant_id=g.tenant_id)

    if estado:
        query = query.filter_by(estado=estado)

    pagination = query.order_by(Lote.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


def _purge_empty_lotes(tenant_id):
    lotes = Lote.query.filter_by(tenant_id=tenant_id).all()
    removed_any = False

    for lote in lotes:
        has_facturas = db.session.query(Factura.id).filter_by(
            tenant_id=tenant_id,
            lote_id=lote.id,
        ).first()
        if has_facturas:
            continue

        db.session.delete(lote)
        removed_any = True

    if removed_any:
        db.session.commit()


@lotes_bp.route('/<uuid:lote_id>', methods=['GET'])
@permission_required('facturas:ver')
def get_lote(lote_id):
    """Obtener un lote con estadísticas."""
    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    # Obtener estadísticas de facturas
    facturas_stats = db.session.query(
        Factura.estado,
        db.func.count(Factura.id)
    ).filter(
        Factura.lote_id == lote_id
    ).group_by(Factura.estado).all()

    stats = {estado: count for estado, count in facturas_stats}

    lote_dict = lote.to_dict()
    lote_dict['stats'] = {
        'pendientes': stats.get('pendiente', 0),
        'autorizadas': stats.get('autorizado', 0),
        'errores': stats.get('error', 0),
        'borradores': stats.get('borrador', 0)
    }

    return jsonify(lote_dict), 200


@lotes_bp.route('/<uuid:lote_id>/facturar', methods=['POST'])
@permission_required('facturar:ejecutar')
def facturar_lote(lote_id):
    """Iniciar el proceso de facturación masiva para un lote."""
    data = request.get_json(silent=True) or {}

    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    if lote.estado == 'procesando':
        return jsonify({'error': 'El lote ya está siendo procesado'}), 400

    # Verificar que hay facturas pendientes
    facturas_pendientes = Factura.query.filter_by(
        tenant_id=g.tenant_id,
        lote_id=lote_id,
        estado='pendiente'
    ).count()

    if facturas_pendientes == 0:
        return jsonify({'error': 'No hay facturas pendientes en este lote'}), 400

    requested_facturador_id = data.get('facturador_id')

    if requested_facturador_id:
        try:
            requested_facturador_id = UUID(str(requested_facturador_id))
        except (ValueError, TypeError):
            return jsonify({'error': 'facturador_id inválido'}), 400

        facturador = Facturador.query.filter_by(
            id=requested_facturador_id,
            tenant_id=g.tenant_id,
            activo=True,
        ).first()

        if not facturador:
            return jsonify({'error': 'Facturador seleccionado no encontrado o inactivo'}), 400

        if not facturador.cert_encrypted or not facturador.key_encrypted:
            return jsonify({'error': 'El facturador seleccionado no tiene certificados cargados'}), 400

        lote.facturador_id = facturador.id
    elif not lote.facturador_id:
        facturador_ids = db.session.query(Factura.facturador_id).filter_by(
            tenant_id=g.tenant_id,
            lote_id=lote_id
        ).filter(Factura.estado == 'pendiente').distinct().all()

        if len(facturador_ids) != 1:
            return jsonify({'error': 'No se puede determinar un facturador unico para el lote'}), 400

        lote.facturador_id = facturador_ids[0][0]

    facturador = Facturador.query.filter_by(
        id=lote.facturador_id,
        tenant_id=g.tenant_id,
        activo=True,
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador del lote no encontrado o inactivo'}), 400

    if not facturador.cert_encrypted or not facturador.key_encrypted:
        return jsonify({'error': 'El facturador del lote no tiene certificados cargados'}), 400

    _assign_facturador_to_pending_facturas(
        lote_id=lote_id,
        tenant_id=g.tenant_id,
        facturador_id=facturador.id,
        punto_venta=facturador.punto_venta,
    )

    # Actualizar estado del lote
    lote.estado = 'procesando'
    log_action('lote:facturar', recurso='lote', recurso_id=lote.id,
               detalle={'etiqueta': lote.etiqueta, 'facturas_pendientes': facturas_pendientes})
    db.session.commit()

    # Disparar tarea de Celery
    from ..tasks.facturacion import procesar_lote
    task = procesar_lote.delay(str(lote_id))

    # Guardar task_id
    lote.celery_task_id = task.id
    db.session.commit()

    return jsonify({
        'message': 'Proceso de facturación iniciado',
        'task_id': task.id,
        'lote': lote.to_dict(),
        'facturador': {
            'id': str(facturador.id),
            'razon_social': facturador.razon_social,
            'cuit': facturador.cuit,
            'punto_venta': facturador.punto_venta,
            'ambiente': facturador.ambiente,
        }
    }), 202


@lotes_bp.route('/<uuid:lote_id>', methods=['DELETE'])
@permission_required('facturas:eliminar')
def delete_lote(lote_id):
    """Eliminar un lote (solo si no tiene facturas autorizadas)."""
    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    # Verificar que no hay facturas autorizadas
    facturas_autorizadas = Factura.query.filter_by(
        lote_id=lote_id,
        estado='autorizado'
    ).count()

    if facturas_autorizadas > 0:
        return jsonify({
            'error': 'No se puede eliminar un lote con facturas autorizadas'
        }), 400

    # Eliminar facturas del lote
    Factura.query.filter_by(lote_id=lote_id).delete()

    log_action('lote:eliminar', recurso='lote', recurso_id=lote.id,
               detalle={'etiqueta': lote.etiqueta})

    # Eliminar lote
    db.session.delete(lote)
    db.session.commit()

    return jsonify({'message': 'Lote eliminado'}), 200


def _assign_facturador_to_pending_facturas(lote_id, tenant_id, facturador_id, punto_venta):
    Factura.query.filter(
        Factura.tenant_id == tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'pendiente',
    ).update(
        {
            Factura.facturador_id: facturador_id,
            Factura.punto_venta: punto_venta,
        },
        synchronize_session=False,
    )
