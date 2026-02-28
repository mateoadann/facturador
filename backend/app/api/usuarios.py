from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Usuario
from ..utils import permission_required
from ..services.permissions import ROLE_PERMISSIONS, ROLES
from ..services.audit import log_action

usuarios_bp = Blueprint('usuarios', __name__)


@usuarios_bp.route('', methods=['GET'])
@permission_required('usuarios:ver')
def list_usuarios():
    """Listar usuarios del tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Usuario.query.filter_by(tenant_id=g.tenant_id)

    pagination = query.order_by(Usuario.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'items': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@usuarios_bp.route('', methods=['POST'])
@permission_required('usuarios:crear')
def create_usuario():
    """Crear un nuevo usuario."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')
    nombre = data.get('nombre', '').strip()
    rol = data.get('rol', 'operator')
    restringir_dashboard_sensible = data.get('restringir_dashboard_sensible', False)

    if not email or not password:
        return jsonify({'error': 'Email y contraseña son requeridos'}), 400

    if len(password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

    if rol not in ROLE_PERMISSIONS:
        return jsonify({'error': f'Rol inválido. Opciones: {", ".join(ROLE_PERMISSIONS.keys())}'}), 400

    if not isinstance(restringir_dashboard_sensible, bool):
        return jsonify({'error': 'restringir_dashboard_sensible debe ser booleano'}), 400

    if rol == 'admin' and restringir_dashboard_sensible:
        return jsonify({'error': 'La restricción solo aplica a usuarios Operador o Solo lectura'}), 400

    existing = Usuario.query.filter_by(tenant_id=g.tenant_id, email=email).first()
    if existing:
        return jsonify({'error': 'Ya existe un usuario con ese email'}), 400

    usuario = Usuario(
        tenant_id=g.tenant_id,
        email=email,
        nombre=nombre,
        rol=rol,
        restringir_dashboard_sensible=restringir_dashboard_sensible,
        activo=True
    )
    usuario.set_password(password)

    db.session.add(usuario)
    log_action('usuario:crear', recurso='usuario', recurso_id=usuario.id,
               detalle={
                   'email': email,
                   'rol': rol,
                   'restringir_dashboard_sensible': restringir_dashboard_sensible,
               })
    db.session.commit()

    return jsonify(usuario.to_dict()), 201


@usuarios_bp.route('/<uuid:usuario_id>', methods=['PUT'])
@permission_required('usuarios:editar')
def update_usuario(usuario_id):
    """Actualizar un usuario."""
    usuario = Usuario.query.filter_by(id=usuario_id, tenant_id=g.tenant_id).first()

    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'email' in data:
        new_email = data['email'].strip()
        existing = Usuario.query.filter(
            Usuario.tenant_id == g.tenant_id,
            Usuario.email == new_email,
            Usuario.id != usuario.id
        ).first()
        if existing:
            return jsonify({'error': 'Ya existe un usuario con ese email'}), 400
        usuario.email = new_email
    if 'rol' in data:
        if data['rol'] not in ROLE_PERMISSIONS:
            return jsonify({'error': 'Rol inválido'}), 400
        if usuario.id == g.current_user.id and data['rol'] != usuario.rol:
            return jsonify({'error': 'No podés cambiar tu propio rol'}), 400
        usuario.rol = data['rol']
        if usuario.rol == 'admin':
            usuario.restringir_dashboard_sensible = False

    if 'restringir_dashboard_sensible' in data:
        value = data.get('restringir_dashboard_sensible')
        if not isinstance(value, bool):
            return jsonify({'error': 'restringir_dashboard_sensible debe ser booleano'}), 400
        target_role = data.get('rol', usuario.rol)
        if target_role == 'admin' and value:
            return jsonify({'error': 'La restricción solo aplica a usuarios Operador o Solo lectura'}), 400
        usuario.restringir_dashboard_sensible = value
    if 'password' in data and data['password']:
        if len(data['password']) < 8:
            return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400
        usuario.set_password(data['password'])

    log_action('usuario:editar', recurso='usuario', recurso_id=usuario.id)
    db.session.commit()

    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route('/<uuid:usuario_id>/toggle-active', methods=['POST'])
@permission_required('usuarios:desactivar')
def toggle_active(usuario_id):
    """Activar/desactivar un usuario."""
    usuario = Usuario.query.filter_by(id=usuario_id, tenant_id=g.tenant_id).first()

    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if usuario.id == g.current_user.id:
        return jsonify({'error': 'No podés desactivarte a vos mismo'}), 400

    usuario.activo = not usuario.activo

    action = 'usuario:activar' if usuario.activo else 'usuario:desactivar'
    log_action(action, recurso='usuario', recurso_id=usuario.id,
               detalle={'email': usuario.email})
    db.session.commit()

    return jsonify(usuario.to_dict()), 200


@usuarios_bp.route('/roles', methods=['GET'])
@permission_required('usuarios:ver')
def list_roles():
    """Listar roles disponibles y sus permisos."""
    roles = {}
    for rol, permisos in ROLE_PERMISSIONS.items():
        roles[rol] = {
            'nombre': ROLES.get(rol, rol),
            'permisos': permisos
        }

    return jsonify({'roles': roles}), 200

