from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from arca_integration.constants import ALICUOTAS_IVA
from flask import Blueprint, request, jsonify, g, current_app, make_response

from ..extensions import db
from ..models import Factura, FacturaItem, Facturador, Receptor, Lote
from ..services.comprobante_rules import (
    es_comprobante_tipo_c,
    normalizar_importes_para_tipo_c,
)
from ..services.comprobante_filename import build_comprobante_pdf_filename
from ..services.csv_parser import parse_csv
from ..services.audit import log_action
from ..utils import permission_required

facturas_bp = Blueprint('facturas', __name__)


@facturas_bp.route('', methods=['GET'])
@permission_required('facturas:ver')
def list_facturas():
    """Listar facturas del tenant con filtros."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    lote_id = request.args.get('lote_id')
    estado = request.args.get('estado')
    facturador_id = request.args.get('facturador_id')
    receptor_id = request.args.get('receptor_id')
    tipo_comprobante = request.args.get('tipo_comprobante', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    estados = request.args.get('estados')

    query = Factura.query.filter_by(tenant_id=g.tenant_id)
    allowed_estados = {'autorizado', 'error', 'pendiente', 'borrador'}

    if lote_id:
        query = query.filter_by(lote_id=lote_id)
    if estados:
        estados_list = [item.strip() for item in estados.split(',') if item.strip()]
        invalid_states = [item for item in estados_list if item not in allowed_estados]
        if invalid_states:
            return jsonify({
                'error': f"Estados inválidos: {', '.join(invalid_states)}"
            }), 400
        query = query.filter(Factura.estado.in_(estados_list))
    elif estado:
        if estado not in allowed_estados:
            return jsonify({'error': f'Estado inválido: {estado}'}), 400
        query = query.filter_by(estado=estado)
    if facturador_id:
        query = query.filter_by(facturador_id=facturador_id)
    if receptor_id:
        query = query.filter_by(receptor_id=receptor_id)
    if tipo_comprobante:
        query = query.filter_by(tipo_comprobante=tipo_comprobante)
    if fecha_desde:
        query = query.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)

    pagination = query.order_by(Factura.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [f.to_dict() for f in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@facturas_bp.route('/<uuid:factura_id>', methods=['GET'])
@permission_required('facturas:ver')
def get_factura(factura_id):
    """Obtener una factura por ID con items."""
    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    return jsonify(factura.to_dict(include_items=True)), 200


@facturas_bp.route('/<uuid:factura_id>/items', methods=['GET'])
@permission_required('facturas:ver')
def get_factura_items(factura_id):
    """Obtener solo los items de una factura."""
    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    return jsonify({
        'items': [item.to_dict() for item in factura.items]
    }), 200


@facturas_bp.route('/<uuid:factura_id>', methods=['PUT'])
@permission_required('facturas:editar')
def update_factura(factura_id):
    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    if factura.estado == 'autorizado':
        return jsonify({'error': 'No se puede editar una factura autorizada'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    try:
        parsed = _parse_factura_update_payload(data, factura, g.tenant_id)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    previous_estado = factura.estado

    for field, value in parsed.items():
        if field == 'items':
            continue
        setattr(factura, field, value)

    items_updated = 'items' in parsed
    if items_updated:
        FacturaItem.query.filter_by(factura_id=factura.id).delete()
        for idx, item_data in enumerate(parsed['items']):
            item = FacturaItem(
                factura_id=factura.id,
                descripcion=item_data['descripcion'],
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario'],
                alicuota_iva_id=item_data['alicuota_iva_id'],
                importe_iva=item_data['importe_iva'],
                subtotal=item_data['subtotal'],
                orden=idx
            )
            db.session.add(item)

    if previous_estado == 'error':
        factura.estado = 'pendiente'
        factura.error_codigo = None
        factura.error_mensaje = None

    log_action(
        'facturas:editar',
        recurso='factura',
        recurso_id=factura.id,
        detalle={
            'estado_anterior': previous_estado,
            'items_editados': items_updated,
        }
    )
    db.session.commit()

    return jsonify(factura.to_dict(include_items=True)), 200


@facturas_bp.route('/<uuid:factura_id>/comprobante-html', methods=['GET'])
@permission_required('facturas:comprobante')
def get_comprobante_html(factura_id):
    """Obtener (y persistir) el HTML del comprobante."""
    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    if factura.estado != 'autorizado':
        return jsonify({'error': 'Solo se puede generar comprobante para facturas autorizadas'}), 400

    force = request.args.get('force', 'false').lower() == 'true'

    try:
        html = _get_or_render_comprobante_html(factura, force=force)
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        return jsonify({'error': f'No se pudo generar el HTML del comprobante: {str(exc)}'}), 400

    return jsonify({
        'factura_id': str(factura.id),
        'html': html,
        'tiene_comprobante_html': bool(html),
    }), 200


@facturas_bp.route('/<uuid:factura_id>/comprobante-pdf', methods=['GET'])
@permission_required('facturas:comprobante')
def get_comprobante_pdf(factura_id):
    """Generar PDF on-demand desde el HTML del comprobante."""
    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    if factura.estado != 'autorizado':
        return jsonify({'error': 'Solo se puede generar PDF para facturas autorizadas'}), 400

    force = request.args.get('force', 'false').lower() == 'true'

    try:
        html = _get_or_render_comprobante_html(factura, force=force)

        from ..services.comprobante_pdf import html_to_pdf_bytes
        pdf_bytes = html_to_pdf_bytes(html)
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        return jsonify({'error': f'No se pudo generar PDF: {str(exc)}'}), 400

    filename = build_comprobante_pdf_filename(factura)

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@facturas_bp.route('/import', methods=['POST'])
@permission_required('facturar:importar')
def import_csv():
    """Importar facturas desde un archivo CSV."""
    if 'file' not in request.files:
        return jsonify({'error': 'Archivo CSV requerido'}), 400

    file = request.files['file']
    etiqueta = (request.form.get('etiqueta', '') or '').strip()
    tipo = request.form.get('tipo', 'factura')

    if not etiqueta:
        return jsonify({'error': 'La etiqueta del lote es requerida'}), 400

    existing_lote = Lote.query.filter(
        Lote.tenant_id == g.tenant_id,
        db.func.lower(Lote.etiqueta) == etiqueta.lower()
    ).first()
    if existing_lote:
        if _is_empty_lote(existing_lote.id, g.tenant_id):
            db.session.delete(existing_lote)
            db.session.flush()
        else:
            return jsonify({'error': 'Ya existe un lote con esa etiqueta'}), 400

    try:
        content = file.read().decode('utf-8')
    except UnicodeDecodeError:
        try:
            file.seek(0)
            content = file.read().decode('latin-1')
        except (UnicodeDecodeError, OSError, ValueError):
            return jsonify({'error': 'No se pudo decodificar el archivo'}), 400

    # Parsear CSV
    facturas_data, parse_errors = parse_csv(content)

    if parse_errors and not facturas_data:
        return jsonify({
            'error': 'Error al parsear CSV',
            'details': parse_errors
        }), 400

    # Crear lote
    lote = Lote(
        tenant_id=g.tenant_id,
        etiqueta=etiqueta,
        tipo=tipo,
        estado='pendiente',
        total_facturas=len(facturas_data)
    )
    db.session.add(lote)
    db.session.flush()

    # Procesar cada factura
    facturas_creadas = []
    errores_creacion = []
    facturador_ids = set()

    for idx, factura_data in enumerate(facturas_data):
        try:
            factura = create_factura_from_data(factura_data, lote.id, g.tenant_id)
            facturas_creadas.append(factura)
            facturador_ids.add(factura.facturador_id)
        except ValueError as e:
            errores_creacion.append(f"Fila {idx + 2}: {str(e)}")

    if len(facturador_ids) > 1:
        db.session.rollback()
        return jsonify({
            'error': 'El lote debe contener facturas de un unico facturador/entorno',
            'details': ['Todas las filas del CSV deben pertenecer al mismo facturador para este lote']
        }), 400

    if facturas_creadas:
        lote.facturador_id = facturas_creadas[0].facturador_id

    lote.total_facturas = len(facturas_creadas)

    log_action('lote:importar', recurso='lote', recurso_id=lote.id,
               detalle={'etiqueta': etiqueta, 'facturas': len(facturas_creadas)})
    db.session.commit()

    return jsonify({
        'lote': lote.to_dict(),
        'facturas_importadas': len(facturas_creadas),
        'errores_parseo': parse_errors,
        'errores_creacion': errores_creacion
    }), 201


def create_factura_from_data(data: dict, lote_id: str, tenant_id: str) -> Factura:
    """Crear una factura a partir de datos parseados del CSV."""

    # Buscar facturador por CUIT, priorizando el ambiente configurado
    facturadores = Facturador.query.filter_by(
        tenant_id=tenant_id,
        cuit=data['facturador_cuit'],
        activo=True
    ).all()

    if not facturadores:
        raise ValueError(f"Facturador con CUIT {data['facturador_cuit']} no encontrado")

    ambiente_preferido = current_app.config.get('ARCA_AMBIENTE', 'testing')
    facturadores_filtrados = [f for f in facturadores if f.ambiente == ambiente_preferido]

    if len(facturadores_filtrados) == 1:
        facturador = facturadores_filtrados[0]
    elif len(facturadores_filtrados) > 1:
        raise ValueError(
            f"Hay múltiples facturadores activos para CUIT {data['facturador_cuit']} en ambiente {ambiente_preferido}. "
            "Desactivá duplicados o ajustá la configuración."
        )
    elif len(facturadores) == 1:
        facturador = facturadores[0]
    else:
        ambientes = ', '.join(sorted({f.ambiente for f in facturadores}))
        raise ValueError(
            f"No hay facturador activo para CUIT {data['facturador_cuit']} en ambiente {ambiente_preferido}. "
            f"Disponibles: {ambientes}"
        )

    # Buscar o crear receptor
    receptor = Receptor.query.filter_by(
        tenant_id=tenant_id,
        doc_nro=data['receptor_cuit']
    ).first()

    if not receptor:
        # Crear receptor con datos mínimos
        receptor = Receptor(
            tenant_id=tenant_id,
            doc_tipo=80,  # CUIT
            doc_nro=data['receptor_cuit'],
            razon_social=data.get('receptor_razon_social', f'CUIT {data["receptor_cuit"]}'),
        )
        db.session.add(receptor)
        db.session.flush()

    importe_neto, importe_iva, importe_total = normalizar_importes_para_tipo_c(
        data['tipo_comprobante'],
        data['importe_neto'],
        data.get('importe_iva', 0),
        data['importe_total'],
    )

    # Crear factura
    factura = Factura(
        tenant_id=tenant_id,
        lote_id=lote_id,
        facturador_id=facturador.id,
        receptor_id=receptor.id,
        tipo_comprobante=data['tipo_comprobante'],
        concepto=data['concepto'],
        punto_venta=facturador.punto_venta,
        fecha_emision=data['fecha_emision'],
        fecha_desde=data.get('fecha_desde'),
        fecha_hasta=data.get('fecha_hasta'),
        fecha_vto_pago=data.get('fecha_vto_pago'),
        importe_total=importe_total,
        importe_neto=importe_neto,
        importe_iva=importe_iva,
        moneda=data.get('moneda', 'PES'),
        cotizacion=data.get('cotizacion', 1),
        cbte_asoc_tipo=data.get('cbte_asoc_tipo'),
        cbte_asoc_pto_vta=data.get('cbte_asoc_pto_vta'),
        cbte_asoc_nro=data.get('cbte_asoc_nro'),
        estado='pendiente'
    )
    db.session.add(factura)
    db.session.flush()

    # Crear items si existen
    if data.get('items'):
        for idx, item_data in enumerate(data['items']):
            item = FacturaItem(
                factura_id=factura.id,
                descripcion=item_data['descripcion'],
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario'],
                alicuota_iva_id=item_data.get('alicuota_iva_id', 5),
                subtotal=item_data['cantidad'] * item_data['precio_unitario'],
                orden=idx
            )
            db.session.add(item)

    return factura


def _get_or_render_comprobante_html(factura: Factura, force: bool = False) -> str:
    if factura.comprobante_html and not force:
        if 'data-template-version="comprobante-v2"' in factura.comprobante_html:
            return factura.comprobante_html

    from ..services.comprobante_renderer import render_comprobante_html
    return render_comprobante_html(factura)


def _parse_factura_update_payload(data: dict, factura: Factura, tenant_id: str) -> dict:
    parsed = {}

    allowed_simple_int = {'receptor_id', 'tipo_comprobante', 'concepto', 'punto_venta', 'cbte_asoc_tipo', 'cbte_asoc_pto_vta', 'cbte_asoc_nro'}
    allowed_decimal = {'importe_total', 'importe_neto', 'importe_iva', 'cotizacion'}
    allowed_date = {'fecha_emision', 'fecha_desde', 'fecha_hasta', 'fecha_vto_pago'}
    allowed_str = {'moneda'}
    allowed_items = {'items'}
    allowed_fields = allowed_simple_int | allowed_decimal | allowed_date | allowed_str | allowed_items

    unknown_fields = set(data.keys()) - allowed_fields
    if unknown_fields:
        raise ValueError(f"Campos no permitidos: {', '.join(sorted(unknown_fields))}")

    if 'receptor_id' in data:
        try:
            receptor_id = UUID(str(data['receptor_id']))
        except (TypeError, ValueError):
            raise ValueError('Receptor inválido')

        receptor = Receptor.query.filter_by(
            id=receptor_id,
            tenant_id=tenant_id
        ).first()
        if not receptor:
            raise ValueError('Receptor inválido')
        parsed['receptor_id'] = receptor.id

    for field in ('tipo_comprobante', 'concepto', 'punto_venta', 'cbte_asoc_tipo', 'cbte_asoc_pto_vta', 'cbte_asoc_nro'):
        if field in data:
            value = data.get(field)
            if value in (None, '') and field.startswith('cbte_asoc_'):
                parsed[field] = None
                continue
            try:
                parsed[field] = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"Campo '{field}' debe ser numérico")

    for field in ('importe_total', 'importe_neto', 'importe_iva', 'cotizacion'):
        if field in data:
            value = data.get(field)
            try:
                parsed[field] = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(f"Campo '{field}' debe ser decimal")
            if parsed[field] < 0:
                raise ValueError(f"Campo '{field}' debe ser mayor o igual a 0")

    for field in ('fecha_emision', 'fecha_desde', 'fecha_hasta', 'fecha_vto_pago'):
        if field in data:
            parsed[field] = _parse_date_or_none(data.get(field), field)

    if 'moneda' in data:
        moneda = (data.get('moneda') or '').strip()
        if not moneda:
            raise ValueError("Campo 'moneda' es requerido")
        parsed['moneda'] = moneda

    if 'items' in data:
        parsed['items'] = _parse_items_payload(data['items'])
        totals = _calculate_totals_from_items(parsed['items'])
        parsed['importe_neto'] = totals['importe_neto']
        parsed['importe_iva'] = totals['importe_iva']
        parsed['importe_total'] = totals['importe_total']

    proposed_tipo = parsed.get('tipo_comprobante', factura.tipo_comprobante)
    proposed_concepto = parsed.get('concepto', factura.concepto)
    proposed_fecha_desde = parsed.get('fecha_desde', factura.fecha_desde)
    proposed_fecha_hasta = parsed.get('fecha_hasta', factura.fecha_hasta)
    proposed_fecha_vto = parsed.get('fecha_vto_pago', factura.fecha_vto_pago)
    proposed_total = parsed.get('importe_total', factura.importe_total)
    proposed_neto = parsed.get('importe_neto', factura.importe_neto)

    if proposed_total < proposed_neto:
        raise ValueError('importe_total debe ser mayor o igual a importe_neto')

    if es_comprobante_tipo_c(proposed_tipo):
        neto, iva, total = normalizar_importes_para_tipo_c(
            proposed_tipo,
            proposed_neto,
            parsed.get('importe_iva', factura.importe_iva),
            proposed_total,
        )
        parsed['importe_neto'] = neto
        parsed['importe_iva'] = iva
        parsed['importe_total'] = total
        proposed_total = total
        proposed_neto = neto

    if proposed_concepto in (2, 3):
        if not (proposed_fecha_desde and proposed_fecha_hasta and proposed_fecha_vto):
            raise ValueError('Para concepto 2 o 3 se requieren fecha_desde, fecha_hasta y fecha_vto_pago')

    tipos_nota = {2, 3, 7, 8, 12, 13, 52, 53}
    if proposed_tipo in tipos_nota:
        cbte_tipo = parsed.get('cbte_asoc_tipo', factura.cbte_asoc_tipo)
        cbte_pto = parsed.get('cbte_asoc_pto_vta', factura.cbte_asoc_pto_vta)
        cbte_nro = parsed.get('cbte_asoc_nro', factura.cbte_asoc_nro)
        if not (cbte_tipo and cbte_pto and cbte_nro):
            raise ValueError('Para notas se requiere cbte_asoc_tipo, cbte_asoc_pto_vta y cbte_asoc_nro')

    return parsed


def _parse_date_or_none(value, field_name: str):
    if value in (None, ''):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
    raise ValueError(f"Campo '{field_name}' debe tener formato YYYY-MM-DD o DD/MM/YYYY")


def _parse_items_payload(items):
    if not isinstance(items, list):
        raise ValueError("Campo 'items' debe ser una lista")

    parsed_items = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f'Item {idx + 1} inválido')

        descripcion = (item.get('descripcion') or '').strip()
        if not descripcion:
            raise ValueError(f'Item {idx + 1}: descripción requerida')

        try:
            cantidad = Decimal(str(item.get('cantidad')))
            precio_unitario = Decimal(str(item.get('precio_unitario')))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f'Item {idx + 1}: cantidad y precio_unitario deben ser decimales')

        if cantidad <= 0:
            raise ValueError(f'Item {idx + 1}: cantidad debe ser mayor a 0')
        if precio_unitario < 0:
            raise ValueError(f'Item {idx + 1}: precio_unitario debe ser mayor o igual a 0')

        try:
            alicuota_iva_id = int(item.get('alicuota_iva_id', 5))
        except (TypeError, ValueError):
            raise ValueError(f'Item {idx + 1}: alicuota_iva_id inválida')

        porcentaje = Decimal(str(ALICUOTAS_IVA.get(alicuota_iva_id, {}).get('porcentaje', 21)))
        subtotal = (cantidad * precio_unitario).quantize(Decimal('0.01'))
        importe_iva = (subtotal * porcentaje / Decimal('100')).quantize(Decimal('0.01'))
        parsed_items.append({
            'descripcion': descripcion,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'alicuota_iva_id': alicuota_iva_id,
            'importe_iva': importe_iva,
            'subtotal': subtotal,
        })

    return parsed_items


def _calculate_totals_from_items(items: list[dict]) -> dict:
    importe_neto = Decimal('0')
    importe_iva = Decimal('0')

    for item in items:
        importe_neto += item['subtotal']
        importe_iva += item['importe_iva']

    importe_neto = importe_neto.quantize(Decimal('0.01'))
    importe_iva = importe_iva.quantize(Decimal('0.01'))
    importe_total = (importe_neto + importe_iva).quantize(Decimal('0.01'))

    return {
        'importe_neto': importe_neto,
        'importe_iva': importe_iva,
        'importe_total': importe_total,
    }


@facturas_bp.route('', methods=['DELETE'])
@permission_required('facturas:eliminar')
def bulk_delete_facturas():
    """Eliminar múltiples facturas (solo borradores y pendientes)."""
    data = request.get_json()

    if not data or not data.get('ids'):
        return jsonify({'error': 'Lista de IDs requerida'}), 400

    ids = data['ids']
    normalized_ids = []
    for factura_id in ids:
        try:
            normalized_ids.append(UUID(str(factura_id)))
        except (TypeError, ValueError):
            return jsonify({'error': 'Lista de IDs inválida'}), 400

    # Solo eliminar facturas en estado borrador o pendiente
    facturas = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.id.in_(normalized_ids),
        Factura.estado.in_(['borrador', 'pendiente'])
    ).all()

    if not facturas:
        return jsonify({'error': 'No se encontraron facturas eliminables'}), 404

    affected_lote_ids = {factura.lote_id for factura in facturas if factura.lote_id}

    deleted_count = 0
    for factura in facturas:
        db.session.delete(factura)
        deleted_count += 1

    db.session.flush()

    deleted_lote_ids = _sync_lotes_after_facturas_delete(affected_lote_ids, g.tenant_id)

    log_action('facturas:eliminar', detalle={'cantidad': deleted_count})
    db.session.commit()

    return jsonify({
        'message': f'{deleted_count} facturas eliminadas',
        'deleted': deleted_count,
        'deleted_lote_ids': deleted_lote_ids,
    }), 200


@facturas_bp.route('/<uuid:factura_id>/enviar-email', methods=['POST'])
@permission_required('email:enviar')
def enviar_email(factura_id):
    """Enviar o reenviar comprobante por email al receptor."""
    from ..models import EmailConfig

    factura = Factura.query.filter_by(
        id=factura_id,
        tenant_id=g.tenant_id
    ).first()

    if not factura:
        return jsonify({'error': 'Factura no encontrada'}), 404

    if factura.estado != 'autorizado':
        return jsonify({'error': 'Solo se pueden enviar comprobantes de facturas autorizadas'}), 400

    if not factura.receptor or not factura.receptor.email:
        return jsonify({'error': 'El receptor no tiene email configurado'}), 400

    config = EmailConfig.query.filter_by(
        tenant_id=g.tenant_id,
        email_habilitado=True,
    ).first()

    if not config:
        return jsonify({'error': 'No hay configuración de email habilitada'}), 400

    from ..tasks.email import enviar_factura_email
    enviar_factura_email.delay(str(factura.id), str(g.tenant_id))

    log_action('email:enviar', recurso='factura', recurso_id=factura.id,
               detalle={'receptor_email': factura.receptor.email})
    db.session.commit()

    return jsonify({
        'message': 'Email en proceso de envío',
        'receptor_email': factura.receptor.email,
    }), 202


def _is_empty_lote(lote_id, tenant_id) -> bool:
    count = Factura.query.filter_by(
        tenant_id=tenant_id,
        lote_id=lote_id,
    ).count()
    return count == 0


def _sync_lotes_after_facturas_delete(lote_ids, tenant_id):
    deleted_lote_ids = []

    for lote_id in lote_ids:
        lote = Lote.query.filter_by(id=lote_id, tenant_id=tenant_id).first()
        if not lote:
            continue

        facturas_lote = Factura.query.filter_by(tenant_id=tenant_id, lote_id=lote_id)
        total = facturas_lote.count()

        if total == 0:
            db.session.delete(lote)
            deleted_lote_ids.append(str(lote_id))
            continue

        stats = db.session.query(
            Factura.estado,
            db.func.count(Factura.id),
        ).filter(
            Factura.tenant_id == tenant_id,
            Factura.lote_id == lote_id,
        ).group_by(Factura.estado).all()

        stats_map = {estado: count for estado, count in stats}
        lote.total_facturas = total
        lote.facturas_ok = stats_map.get('autorizado', 0)
        lote.facturas_error = stats_map.get('error', 0)

    return deleted_lote_ids
