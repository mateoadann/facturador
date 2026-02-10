from flask import Blueprint, request, jsonify, g, current_app, make_response
from ..extensions import db
from ..models import Factura, FacturaItem, Facturador, Receptor, Lote
from ..services.csv_parser import parse_csv
from ..utils import tenant_required

facturas_bp = Blueprint('facturas', __name__)


@facturas_bp.route('', methods=['GET'])
@tenant_required
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

    query = Factura.query.filter_by(tenant_id=g.tenant_id)

    if lote_id:
        query = query.filter_by(lote_id=lote_id)
    if estado:
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
@tenant_required
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
@tenant_required
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


@facturas_bp.route('/<uuid:factura_id>/comprobante-html', methods=['GET'])
@tenant_required
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
    except Exception as e:
        return jsonify({'error': f'No se pudo generar el HTML del comprobante: {str(e)}'}), 400

    return jsonify({
        'factura_id': str(factura.id),
        'html': html,
        'tiene_comprobante_html': bool(html),
    }), 200


@facturas_bp.route('/<uuid:factura_id>/comprobante-pdf', methods=['GET'])
@tenant_required
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
    except Exception as e:
        return jsonify({'error': f'No se pudo generar PDF: {str(e)}'}), 400

    punto_venta = int(factura.punto_venta or 0)
    numero = int(factura.numero_comprobante or 0)
    filename = f'comprobante-{punto_venta:05d}-{numero:08d}.pdf'

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@facturas_bp.route('/import', methods=['POST'])
@tenant_required
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
        except Exception:
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
        importe_total=data['importe_total'],
        importe_neto=data['importe_neto'],
        importe_iva=data.get('importe_iva', 0),
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

    factura.comprobante_html = render_comprobante_html(factura)
    db.session.commit()
    return factura.comprobante_html


@facturas_bp.route('', methods=['DELETE'])
@tenant_required
def bulk_delete_facturas():
    """Eliminar múltiples facturas (solo borradores y pendientes)."""
    data = request.get_json()

    if not data or not data.get('ids'):
        return jsonify({'error': 'Lista de IDs requerida'}), 400

    ids = data['ids']

    # Solo eliminar facturas en estado borrador o pendiente
    facturas = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.id.in_(ids),
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

    db.session.commit()

    return jsonify({
        'message': f'{deleted_count} facturas eliminadas',
        'deleted': deleted_count,
        'deleted_lote_ids': deleted_lote_ids,
    }), 200


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
