from functools import wraps
from uuid import UUID
from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models import Usuario


def _load_user():
    """Carga usuario desde JWT y lo setea en g. Retorna (usuario, error_response)."""
    verify_jwt_in_request()

    user_id = get_jwt_identity()
    try:
        user_id = UUID(str(user_id))
    except (TypeError, ValueError):
        return None, (jsonify({'error': 'Token inválido'}), 401)

    usuario = Usuario.query.get(user_id)

    if not usuario:
        return None, (jsonify({'error': 'Usuario no encontrado'}), 404)

    if not usuario.activo:
        return None, (jsonify({'error': 'Usuario desactivado'}), 403)

    g.current_user = usuario
    g.tenant_id = usuario.tenant_id
    return usuario, None


def tenant_required(f):
    """
    Decorador que verifica que el usuario tiene acceso al tenant.
    Carga el usuario y tenant en g.current_user y g.tenant_id.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario, error = _load_user()
        if error:
            return error
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorador que verifica que el usuario es administrador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario, error = _load_user()
        if error:
            return error

        if usuario.rol != 'admin':
            return jsonify({'error': 'Acceso denegado. Se requiere rol de administrador'}), 403

        return f(*args, **kwargs)

    return decorated_function


def permission_required(*permissions):
    """
    Decorador que verifica JWT + tenant + permisos del rol.
    Uso: @permission_required('facturadores:crear')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario, error = _load_user()
            if error:
                return error

            from ..services.permissions import has_permission
            for perm in permissions:
                if not has_permission(usuario.rol, perm):
                    return jsonify({'error': 'Permiso insuficiente'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
