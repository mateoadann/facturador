from datetime import datetime
from uuid import UUID
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from ..extensions import db
from ..models import Usuario

auth_bp = Blueprint('auth', __name__)


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

    if not usuario or not usuario.check_password(password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    if not usuario.activo:
        return jsonify({'error': 'Usuario desactivado'}), 403

    # Actualizar último login
    usuario.ultimo_login = datetime.utcnow()
    db.session.commit()

    # Crear tokens
    access_token = create_access_token(identity=str(usuario.id))
    refresh_token = create_refresh_token(identity=str(usuario.id))

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': usuario.to_dict(),
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
        'user': usuario.to_dict(),
        'tenant': usuario.tenant.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Cerrar sesión (client-side debe eliminar tokens)."""
    # En una implementación más robusta, se podría agregar el token a una blacklist
    return jsonify({'message': 'Sesión cerrada exitosamente'}), 200
