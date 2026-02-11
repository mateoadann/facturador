from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import EmailConfig
from ..services.encryption import encrypt_certificate
from ..services.email_service import test_smtp_connection, send_test_email
from ..utils import permission_required
from ..services.audit import log_action

email_bp = Blueprint('email', __name__)


@email_bp.route('/config', methods=['GET'])
@permission_required('email:configurar')
def get_config():
    """Obtener configuración de email del tenant."""
    config = EmailConfig.query.filter_by(tenant_id=g.tenant_id).first()

    if not config:
        return jsonify({'configured': False}), 200

    data = config.to_dict()
    data['configured'] = True
    return jsonify(data), 200


@email_bp.route('/config', methods=['PUT'])
@permission_required('email:configurar')
def update_config():
    """Crear o actualizar configuración de email del tenant."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    required = ['smtp_host', 'smtp_user', 'from_email']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'El campo {field} es requerido'}), 400

    smtp_port = data.get('smtp_port', 587)
    if not isinstance(smtp_port, int) or smtp_port < 1 or smtp_port > 65535:
        return jsonify({'error': 'Puerto SMTP inválido'}), 400

    config = EmailConfig.query.filter_by(tenant_id=g.tenant_id).first()

    if config:
        config.smtp_host = data['smtp_host']
        config.smtp_port = smtp_port
        config.smtp_use_tls = data.get('smtp_use_tls', True)
        config.smtp_user = data['smtp_user']
        config.from_email = data['from_email']
        config.from_name = data.get('from_name', '')
        config.email_habilitado = data.get('email_habilitado', True)

        if data.get('smtp_password'):
            config.smtp_password_encrypted = encrypt_certificate(
                data['smtp_password'].encode('utf-8')
            )
    else:
        if not data.get('smtp_password'):
            return jsonify({'error': 'La contraseña SMTP es requerida'}), 400

        config = EmailConfig(
            tenant_id=g.tenant_id,
            smtp_host=data['smtp_host'],
            smtp_port=smtp_port,
            smtp_use_tls=data.get('smtp_use_tls', True),
            smtp_user=data['smtp_user'],
            smtp_password_encrypted=encrypt_certificate(
                data['smtp_password'].encode('utf-8')
            ),
            from_email=data['from_email'],
            from_name=data.get('from_name', ''),
            email_habilitado=data.get('email_habilitado', True),
        )
        db.session.add(config)

    db.session.flush()
    log_action('email:configurar', recurso='email_config', recurso_id=config.id,
               detalle={'smtp_host': config.smtp_host, 'from_email': config.from_email})
    db.session.commit()

    result = config.to_dict()
    result['configured'] = True
    return jsonify(result), 200


@email_bp.route('/test', methods=['POST'])
@permission_required('email:configurar')
def test_connection():
    """Testear conexión SMTP."""
    config = EmailConfig.query.filter_by(tenant_id=g.tenant_id).first()

    if not config:
        return jsonify({'error': 'No hay configuración de email'}), 400

    result = test_smtp_connection(config)
    return jsonify(result), 200 if result['success'] else 400


@email_bp.route('/test-send', methods=['POST'])
@permission_required('email:configurar')
def test_send():
    """Enviar email de prueba."""
    data = request.get_json()

    if not data or not data.get('to_email'):
        return jsonify({'error': 'El campo to_email es requerido'}), 400

    config = EmailConfig.query.filter_by(tenant_id=g.tenant_id).first()

    if not config:
        return jsonify({'error': 'No hay configuración de email'}), 400

    try:
        send_test_email(config, data['to_email'])
        return jsonify({'success': True, 'message': 'Email de prueba enviado'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
