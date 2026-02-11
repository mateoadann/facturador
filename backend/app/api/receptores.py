from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Receptor, Facturador
from ..services.encryption import decrypt_certificate
from ..utils import permission_required
from ..services.audit import log_action

receptores_bp = Blueprint('receptores', __name__)


@receptores_bp.route('', methods=['GET'])
@permission_required('receptores:ver')
def list_receptores():
    """Listar receptores del tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    activo = request.args.get('activo', type=str)

    query = Receptor.query.filter_by(tenant_id=g.tenant_id)

    if search:
        query = query.filter(
            db.or_(
                Receptor.razon_social.ilike(f'%{search}%'),
                Receptor.doc_nro.ilike(f'%{search}%')
            )
        )

    if activo is not None:
        query = query.filter_by(activo=activo.lower() == 'true')

    pagination = query.order_by(Receptor.razon_social).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@receptores_bp.route('/<uuid:receptor_id>', methods=['GET'])
@permission_required('receptores:ver')
def get_receptor(receptor_id):
    """Obtener un receptor por ID."""
    receptor = Receptor.query.filter_by(
        id=receptor_id,
        tenant_id=g.tenant_id
    ).first()

    if not receptor:
        return jsonify({'error': 'Receptor no encontrado'}), 404

    return jsonify(receptor.to_dict()), 200


@receptores_bp.route('', methods=['POST'])
@permission_required('receptores:crear')
def create_receptor():
    """Crear un nuevo receptor."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    required_fields = ['doc_nro', 'razon_social']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} es requerido'}), 400

    # Limpiar CUIT
    doc_nro = data['doc_nro'].replace('-', '').replace(' ', '')

    # Verificar que no exista otro receptor con el mismo documento
    existing = Receptor.query.filter_by(
        tenant_id=g.tenant_id,
        doc_nro=doc_nro
    ).first()

    if existing:
        return jsonify({'error': 'Ya existe un receptor con ese documento'}), 400

    receptor = Receptor(
        tenant_id=g.tenant_id,
        doc_tipo=data.get('doc_tipo', 80),
        doc_nro=doc_nro,
        razon_social=data['razon_social'],
        direccion=data.get('direccion'),
        condicion_iva=data.get('condicion_iva'),
        email=data.get('email')
    )

    db.session.add(receptor)
    db.session.flush()
    log_action('receptor:crear', recurso='receptor', recurso_id=receptor.id,
               detalle={'doc_nro': doc_nro, 'razon_social': data['razon_social']})
    db.session.commit()

    return jsonify(receptor.to_dict()), 201


@receptores_bp.route('/<uuid:receptor_id>', methods=['PUT'])
@permission_required('receptores:editar')
def update_receptor(receptor_id):
    """Actualizar un receptor."""
    receptor = Receptor.query.filter_by(
        id=receptor_id,
        tenant_id=g.tenant_id
    ).first()

    if not receptor:
        return jsonify({'error': 'Receptor no encontrado'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    # Campos actualizables
    if 'razon_social' in data:
        receptor.razon_social = data['razon_social']
    if 'direccion' in data:
        receptor.direccion = data['direccion']
    if 'condicion_iva' in data:
        receptor.condicion_iva = data['condicion_iva']
    if 'email' in data:
        receptor.email = data['email']
    if 'activo' in data:
        receptor.activo = data['activo']

    log_action('receptor:editar', recurso='receptor', recurso_id=receptor.id)
    db.session.commit()

    return jsonify(receptor.to_dict()), 200


@receptores_bp.route('/<uuid:receptor_id>', methods=['DELETE'])
@permission_required('receptores:eliminar')
def delete_receptor(receptor_id):
    """Desactivar un receptor."""
    receptor = Receptor.query.filter_by(
        id=receptor_id,
        tenant_id=g.tenant_id
    ).first()

    if not receptor:
        return jsonify({'error': 'Receptor no encontrado'}), 404

    # Soft delete
    receptor.activo = False
    log_action('receptor:eliminar', recurso='receptor', recurso_id=receptor.id,
               detalle={'doc_nro': receptor.doc_nro, 'razon_social': receptor.razon_social})
    db.session.commit()

    return jsonify({'message': 'Receptor desactivado'}), 200


@receptores_bp.route('/consultar-cuit', methods=['POST'])
@permission_required('receptores:ver')
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
