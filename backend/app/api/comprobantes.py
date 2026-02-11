from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Facturador
from ..services.encryption import decrypt_certificate
from ..utils import permission_required

comprobantes_bp = Blueprint('comprobantes', __name__)


@comprobantes_bp.route('/consultar', methods=['POST'])
@permission_required('comprobantes:consultar')
def consultar_comprobante():
    """Consultar un comprobante existente en ARCA."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    required_fields = ['facturador_id', 'tipo_comprobante', 'punto_venta', 'numero']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo {field} es requerido'}), 400

    facturador = Facturador.query.filter_by(
        id=data['facturador_id'],
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    if not facturador.cert_encrypted or not facturador.key_encrypted:
        return jsonify({'error': 'El facturador no tiene certificados cargados'}), 400

    try:
        from arca_integration import ArcaClient
        from arca_integration.services import WSFEService

        cert = decrypt_certificate(facturador.cert_encrypted)
        key = decrypt_certificate(facturador.key_encrypted)

        client = ArcaClient(
            cuit=facturador.cuit,
            cert=cert,
            key=key,
            ambiente=facturador.ambiente
        )

        wsfe = WSFEService(client)
        result = wsfe.consultar_comprobante(
            tipo_cbte=data['tipo_comprobante'],
            punto_venta=data['punto_venta'],
            numero=data['numero']
        )

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al consultar comprobante: {str(e)}'
        }), 400


@comprobantes_bp.route('/ultimo-autorizado', methods=['POST'])
@permission_required('comprobantes:consultar')
def ultimo_autorizado():
    """Consultar el último número de comprobante autorizado."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    facturador_id = data.get('facturador_id')
    tipo_comprobante = data.get('tipo_comprobante')

    if not facturador_id or not tipo_comprobante:
        return jsonify({'error': 'facturador_id y tipo_comprobante son requeridos'}), 400

    facturador = Facturador.query.filter_by(
        id=facturador_id,
        tenant_id=g.tenant_id
    ).first()

    if not facturador:
        return jsonify({'error': 'Facturador no encontrado'}), 404

    if not facturador.cert_encrypted:
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

        ultimo = client.fe_comp_ultimo_autorizado(
            punto_venta=facturador.punto_venta,
            tipo_cbte=tipo_comprobante
        )

        return jsonify({
            'success': True,
            'ultimo_autorizado': ultimo,
            'proximo': ultimo + 1
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al consultar: {str(e)}'
        }), 400
