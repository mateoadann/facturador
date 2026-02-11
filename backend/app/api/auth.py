from datetime import datetime, timedelta
from uuid import UUID
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from ..extensions import db
from ..models import Usuario
from ..utils import tenant_required
from ..services.audit import log_action

auth_bp = Blueprint('auth', __name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


@auth_bp.route('/login', methods=['POST'])
def login():
    """Autenticar usuario y retornar tokens."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario:
        return jsonify({'error': 'Credenciales inválidas'}), 401

    # Verificar lockout
    if usuario.locked_until and usuario.locked_until > datetime.utcnow():
        remaining = (usuario.locked_until - datetime.utcnow()).seconds // 60 + 1
        return jsonify({'error': f'Cuenta bloqueada. Intentá de nuevo en {remaining} minutos'}), 429

    if not usuario.check_password(password):
        # Incrementar intentos fallidos
        usuario.login_attempts = (usuario.login_attempts or 0) + 1
        if usuario.login_attempts >= MAX_LOGIN_ATTEMPTS:
            usuario.locked_until = datetime.utcnow() + LOCKOUT_DURATION

        # Auditoría de login fallido
        g.current_user = usuario
        g.tenant_id = usuario.tenant_id
        log_action('login:fallido', detalle={'intentos': usuario.login_attempts})
        db.session.commit()
        return jsonify({'error': 'Credenciales inválidas'}), 401

    if not usuario.activo:
        return jsonify({'error': 'Usuario desactivado'}), 403

    # Login exitoso: resetear contadores
    usuario.login_attempts = 0
    usuario.locked_until = None
    usuario.ultimo_login = datetime.utcnow()

    # Crear tokens
    access_token = create_access_token(identity=str(usuario.id))
    refresh_token = create_refresh_token(identity=str(usuario.id))

    # Auditoría
    g.current_user = usuario
    g.tenant_id = usuario.tenant_id
    log_action('login:exitoso')
    db.session.commit()

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': usuario.to_dict(include_permissions=True),
        'tenant': usuario.tenant.to_dict()
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Renovar access token usando refresh token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    return jsonify({
        'access_token': access_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Obtener información del usuario actual."""
    user_id = get_jwt_identity()
    try:
        user_id = UUID(str(user_id))
    except (TypeError, ValueError):
        return jsonify({'error': 'Token inválido'}), 401

    usuario = Usuario.query.get(user_id)

    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    return jsonify({
        'user': usuario.to_dict(include_permissions=True),
        'tenant': usuario.tenant.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@tenant_required
def logout():
    """Cerrar sesión (client-side debe eliminar tokens)."""
    log_action('logout')
    db.session.commit()
    return jsonify({'message': 'Sesión cerrada exitosamente'}), 200


@auth_bp.route('/change-password', methods=['POST'])
@tenant_required
def change_password():
    """Cambiar contraseña del usuario autenticado."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Contraseña actual y nueva son requeridas'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    if not g.current_user.check_password(current_password):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 401

    g.current_user.set_password(new_password)
    g.current_user.password_changed_at = datetime.utcnow()

    log_action('password:cambio')
    db.session.commit()

    return jsonify({'message': 'Contraseña actualizada'}), 200
