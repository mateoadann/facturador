from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Facturador
from ..services.encryption import encrypt_certificate, decrypt_certificate
from ..utils import permission_required
from ..services.audit import log_action

facturadores_bp = Blueprint('facturadores', __name__)


@facturadores_bp.route('', methods=['GET'])
@permission_required('facturadores:ver')
def list_facturadores():
    """Listar facturadores del tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    activo = request.args.get('activo', type=str)

    query = Facturador.query.filter_by(tenant_id=g.tenant_id)

    if activo is not None:
        query = query.filter_by(activo=activo.lower() == 'true')

    pagination = query.order_by(Facturador.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [f.to_dict() for f in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@facturadores_bp.route('/<uuid:facturador_id>', methods=['GET'])
@permission_required('facturadores:ver')
def get_facturador(facturador_id):
    """Obtener un facturador por ID."""
    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    return jsonify(facturador.to_dict()), 200


@facturadores_bp.route('', methods=['POST'])
@permission_required('facturadores:crear')
def create_facturador():
    """Crear un nuevo facturador."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    required_fields = ['cuit', 'razon_social', 'punto_venta']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} es requerido'}), 400

    ambiente = data.get('ambiente', 'testing')

    # Verificar que no exista otro facturador con el mismo CUIT, punto de venta y ambiente
    existing = Facturador.query.filter_by(
        tenant_id=g.tenant_id,
        cuit=data['cuit'],
        punto_venta=data['punto_venta'],
        ambiente=ambiente,
    ).first()

    if existing:
        return jsonify({'error': 'Ya existe un facturador con ese CUIT, punto de venta y ambiente'}), 400

    facturador = Facturador(
        tenant_id=g.tenant_id,
        cuit=data['cuit'],
        razon_social=data['razon_social'],
        direccion=data.get('direccion'),
        condicion_iva=data.get('condicion_iva'),
        punto_venta=data['punto_venta'],
        ambiente=ambiente
    )

    db.session.add(facturador)
    db.session.flush()
    log_action('facturador:crear', recurso='facturador', recurso_id=facturador.id,
               detalle={'cuit': data['cuit'], 'razon_social': data['razon_social']})
    db.session.commit()

    return jsonify(facturador.to_dict()), 201


@facturadores_bp.route('/<uuid:facturador_id>', methods=['PUT'])
@permission_required('facturadores:editar')
def update_facturador(facturador_id):
    """Actualizar un facturador."""
    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    nuevo_punto_venta = facturador.punto_venta
    if 'punto_venta' in data:
        try:
            nuevo_punto_venta = int(data['punto_venta'])
        except (TypeError, ValueError):
            return jsonify({'error': 'punto_venta debe ser numérico'}), 400

        if nuevo_punto_venta <= 0:
            return jsonify({'error': 'punto_venta debe ser mayor a 0'}), 400

    nuevo_ambiente = data.get('ambiente', facturador.ambiente)

    if 'punto_venta' in data or 'ambiente' in data:
        existing = Facturador.query.filter(
            Facturador.tenant_id == g.tenant_id,
            Facturador.cuit == facturador.cuit,
            Facturador.punto_venta == nuevo_punto_venta,
            Facturador.ambiente == nuevo_ambiente,
            Facturador.id != facturador.id,
        ).first()

        if existing:
            return jsonify({'error': 'Ya existe un facturador con ese CUIT, punto de venta y ambiente'}), 400

    # Campos actualizables
    if 'razon_social' in data:
        facturador.razon_social = data['razon_social']
    if 'direccion' in data:
        facturador.direccion = data['direccion']
    if 'condicion_iva' in data:
        facturador.condicion_iva = data['condicion_iva']
    if 'punto_venta' in data:
        facturador.punto_venta = nuevo_punto_venta
    if 'ambiente' in data:
        facturador.ambiente = nuevo_ambiente
    if 'activo' in data:
        facturador.activo = data['activo']

    log_action('facturador:editar', recurso='facturador', recurso_id=facturador.id)
    db.session.commit()

    return jsonify(facturador.to_dict()), 200


@facturadores_bp.route('/<uuid:facturador_id>', methods=['DELETE'])
@permission_required('facturadores:eliminar')
def delete_facturador(facturador_id):
    """Desactivar un facturador."""
    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    # Soft delete
    facturador.activo = False
    log_action('facturador:desactivar', recurso='facturador', recurso_id=facturador.id,
               detalle={'cuit': facturador.cuit, 'razon_social': facturador.razon_social})
    db.session.commit()

    return jsonify({'message': 'Facturador desactivado'}), 200


@facturadores_bp.route('/<uuid:facturador_id>/certificados', methods=['POST'])
@permission_required('facturadores:certificados')
def upload_certificados(facturador_id):
    """Subir certificados (cert y key) para un facturador."""
    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    if 'cert' not in request.files or 'key' not in request.files:
        return jsonify({'error': 'Se requieren archivos cert y key'}), 400

    cert_file = request.files['cert']
    key_file = request.files['key']

    try:
        cert_data = cert_file.read()
        key_data = key_file.read()

        facturador.cert_encrypted = encrypt_certificate(cert_data)
        facturador.key_encrypted = encrypt_certificate(key_data)

        log_action('facturador:certificados', recurso='facturador', recurso_id=facturador.id,
                   detalle={'cuit': facturador.cuit})
        db.session.commit()

        return jsonify({
            'message': 'Certificados cargados exitosamente',
            'facturador': facturador.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error al procesar certificados: {str(e)}'}), 500


@facturadores_bp.route('/<uuid:facturador_id>/test-conexion', methods=['POST'])
@permission_required('facturadores:ver')
def test_conexion(facturador_id):
    """Probar conexión con ARCA para un facturador."""
    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    if not facturador.cert_encrypted or not facturador.key_encrypted:
        return jsonify({'error': 'El facturador no tiene certificados cargados'}), 400

    try:
        from arca_integration import ArcaClient

        cert = decrypt_certificate(facturador.cert_encrypted)
        key = decrypt_certificate(facturador.key_encrypted)

        client = ArcaClient(
            cuit=facturador.cuit,
            cert=cert,
            key=key,
            ambiente=facturador.ambiente
        )

        # Test de conexión - obtener último comprobante autorizado
        result = client.fe_comp_ultimo_autorizado(
            punto_venta=facturador.punto_venta,
            tipo_cbte=1  # Factura A
        )

        return jsonify({
            'success': True,
            'message': 'Conexión exitosa con ARCA',
            'ultimo_comprobante': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error de conexión: {str(e)}'
        }), 400


@facturadores_bp.route('/consultar-cuit', methods=['POST'])
@permission_required('facturadores:ver')
def consultar_cuit():
    """Consultar datos de un CUIT en el padrón de ARCA."""
    data = request.get_json()

    if not data or not data.get('cuit'):
        return jsonify({'error': 'CUIT es requerido'}), 400

    cuit = data['cuit'].replace('-', '').replace(' ', '')

    try:
        from arca_integration import ArcaClient

        # Usar cualquier facturador del tenant para la consulta
        facturador = Facturador.query.filter_by(
            tenant_id=g.tenant_id,
            activo=True
        ).first()

        if not facturador or not facturador.cert_encrypted:
            return jsonify({'error': 'Se requiere un facturador con certificados para consultar'}), 400

        cert = decrypt_certificate(facturador.cert_encrypted)
        key = decrypt_certificate(facturador.key_encrypted)

        client = ArcaClient(
            cuit=facturador.cuit,
            cert=cert,
            key=key,
            ambiente=facturador.ambiente
        )

        result = client.consultar_padron(cuit)

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al consultar CUIT: {str(e)}'
        }), 400
