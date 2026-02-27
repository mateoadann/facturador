from uuid import UUID

from flask import Blueprint, request, jsonify, g
from celery.result import AsyncResult

from ..extensions import db, celery
from ..models import Lote, Factura, Facturador, EmailConfig
from ..utils import permission_required
from ..services.audit import log_action

lotes_bp = Blueprint('lotes', __name__)


ACTIVE_TASK_STATES = {'STARTED', 'PROGRESS', 'RETRY'}


@lotes_bp.route('', methods=['GET'])
@permission_required('facturas:ver')
def list_lotes():
    """Listar lotes del tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')
    para_facturar = request.args.get('para_facturar', 'false').lower() == 'true'
    para_email = request.args.get('para_email', 'false').lower() == 'true'

    query = Lote.query.filter_by(tenant_id=g.tenant_id)

    if para_facturar:
        retryable_lote_ids = db.session.query(Factura.lote_id).filter(
            Factura.tenant_id == g.tenant_id,
            Factura.estado.in_(['pendiente', 'error']),
        ).distinct()
        query = query.filter(Lote.id.in_(retryable_lote_ids))
    elif para_email:
        emailable_lote_ids = db.session.query(Factura.lote_id).filter(
            Factura.tenant_id == g.tenant_id,
            Factura.estado == 'autorizado',
        ).distinct()
        query = query.filter(Lote.id.in_(emailable_lote_ids))
    elif estado:
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
        Factura.tenant_id == g.tenant_id,
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
        if _lote_task_activa(lote.celery_task_id):
            return jsonify({'error': 'El lote ya está siendo procesado'}), 400

        # Si quedó "colgado" en procesando por falla previa, permitir reanudar
        lote.estado = 'error'
        db.session.flush()

    # Verificar que hay facturas reintentables
    facturas_reintentables = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado.in_(['pendiente', 'error'])
    ).count()

    if facturas_reintentables == 0:
        return jsonify({'error': 'No hay facturas pendientes o con error en este lote'}), 400

    # Resetear facturas en error para permitir reintento
    Factura.query.filter_by(
        tenant_id=g.tenant_id,
        lote_id=lote_id,
        estado='error'
    ).update(
        {
            Factura.estado: 'pendiente',
            Factura.error_codigo: None,
            Factura.error_mensaje: None,
        },
        synchronize_session=False,
    )

    facturas_pendientes = Factura.query.filter_by(
        tenant_id=g.tenant_id,
        lote_id=lote_id,
        estado='pendiente'
    ).count()

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
    task = procesar_lote.delay(str(lote_id), str(g.tenant_id))

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


def _lote_task_activa(task_id: str | None) -> bool:
    """Determina si la tarea de Celery asociada al lote sigue activa."""
    if not task_id:
        return False

    task = AsyncResult(task_id, app=celery)
    return task.status in ACTIVE_TASK_STATES


@lotes_bp.route('/<uuid:lote_id>/enviar-emails', methods=['POST'])
@permission_required('email:enviar')
def enviar_emails_lote_api(lote_id):
    """Iniciar el envio masivo de emails de comprobantes de un lote."""
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'no_enviados')

    if mode not in ['todos', 'no_enviados']:
        return jsonify({'error': 'mode invalido. Valores permitidos: todos, no_enviados'}), 400

    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id,
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    config = EmailConfig.query.filter_by(
        tenant_id=g.tenant_id,
        email_habilitado=True,
    ).first()
    if not config:
        return jsonify({'error': 'No hay configuracion de email habilitada'}), 400

    facturas_query = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    )

    if mode == 'no_enviados':
        facturas_query = facturas_query.filter(Factura.email_enviado.is_(False))

    elegibles = [
        factura for factura in facturas_query.all()
        if factura.receptor and factura.receptor.email
    ]

    if not elegibles:
        return jsonify({'error': 'No hay facturas elegibles para enviar'}), 400

    from ..tasks.email import enviar_emails_lote as enviar_emails_lote_task
    task = enviar_emails_lote_task.delay(str(lote_id), str(g.tenant_id), mode)

    log_action(
        'email:enviar',
        recurso='lote',
        recurso_id=lote.id,
        detalle={
            'mode': mode,
            'facturas_elegibles': len(elegibles),
            'task_id': task.id,
        }
    )
    db.session.commit()

    return jsonify({
        'message': 'Envio masivo de emails iniciado',
        'task_id': task.id,
        'mode': mode,
        'facturas_elegibles': len(elegibles),
    }), 202


@lotes_bp.route('/<uuid:lote_id>/email-preview', methods=['GET'])
@permission_required('email:enviar')
def email_preview_lote(lote_id):
    """Obtener contadores de envio de emails para un lote."""
    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id,
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    autorizadas = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    )

    autorizadas_list = autorizadas.all()
    autorizadas_total = len(autorizadas_list)

    autorizadas_con_email_total = sum(
        1
        for factura in autorizadas_list
        if factura.receptor and factura.receptor.email and factura.receptor.email.strip()
    )

    enviar_no_enviados = sum(
        1
        for factura in autorizadas_list
        if (
            factura.receptor
            and factura.receptor.email
            and factura.receptor.email.strip()
            and not factura.email_enviado
        )
    )

    return jsonify({
        'lote_id': str(lote.id),
        'autorizados': autorizadas_total,
        'autorizados_con_email': autorizadas_con_email_total,
        'autorizados_sin_email': autorizadas_total - autorizadas_con_email_total,
        'enviar_todos': autorizadas_con_email_total,
        'enviar_no_enviados': enviar_no_enviados,
    }), 200


@lotes_bp.route('/<uuid:lote_id>/comprobantes-zip-preview', methods=['GET'])
@permission_required('facturas:comprobante')
def comprobantes_zip_preview(lote_id):
    """Obtener cantidad de comprobantes autorizados para ZIP por lote."""
    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id,
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    autorizados = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    ).count()

    return jsonify({
        'lote_id': str(lote.id),
        'autorizados': autorizados,
    }), 200


@lotes_bp.route('/<uuid:lote_id>/comprobantes-zip', methods=['POST'])
@permission_required('facturas:comprobante')
def generar_comprobantes_zip(lote_id):
    """Encola la generacion async de ZIP de comprobantes autorizados de un lote."""
    lote = Lote.query.filter_by(
        id=lote_id,
        tenant_id=g.tenant_id,
    ).first()

    if not lote:
        return jsonify({'error': 'Lote no encontrado'}), 404

    autorizados = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    ).count()

    if autorizados == 0:
        return jsonify({'error': 'El lote no tiene comprobantes autorizados para descargar'}), 400

    from ..tasks.downloads import generar_comprobantes_zip_lote
    task = generar_comprobantes_zip_lote.delay(str(lote.id), str(g.tenant_id))

    log_action(
        'facturas:comprobante',
        recurso='lote',
        recurso_id=lote.id,
        detalle={
            'accion': 'descarga_zip',
            'task_id': task.id,
            'autorizados': autorizados,
        }
    )
    db.session.commit()

    return jsonify({
        'message': 'Generacion de ZIP encolada',
        'task_id': task.id,
        'autorizados': autorizados,
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
        tenant_id=g.tenant_id,
        lote_id=lote_id,
        estado='autorizado'
    ).count()

    if facturas_autorizadas > 0:
        return jsonify({
            'error': 'No se puede eliminar un lote con facturas autorizadas'
        }), 400

    # Eliminar facturas del lote
    Factura.query.filter_by(
        tenant_id=g.tenant_id,
        lote_id=lote_id,
    ).delete()

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
