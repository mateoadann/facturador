from functools import wraps
from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models import Usuario


def tenant_required(f):
    """
    Decorador que verifica que el usuario tiene acceso al tenant.
    Carga el usuario y tenant en g.current_user y g.tenant_id.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()

        user_id = get_jwt_identity()
        usuario = Usuario.query.get(user_id)

        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        if not usuario.activo:
            return jsonify({'error': 'Usuario desactivado'}), 403

        g.current_user = usuario
        g.tenant_id = usuario.tenant_id

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorador que verifica que el usuario es administrador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()

        user_id = get_jwt_identity()
        usuario = Usuario.query.get(user_id)

        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        if usuario.rol != 'admin':
            return jsonify({'error': 'Acceso denegado. Se requiere rol de administrador'}), 403

        g.current_user = usuario
        g.tenant_id = usuario.tenant_id

        return f(*args, **kwargs)

    return decorated_function
