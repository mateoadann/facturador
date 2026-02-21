# Definicion centralizada de permisos y roles

PERMISSIONS = {
    # Dashboard
    'dashboard:ver': 'Ver dashboard y estadisticas',

    # Facturacion
    'facturar:importar': 'Importar CSV de facturas',
    'facturar:ejecutar': 'Ejecutar facturacion masiva',
    'facturas:ver': 'Ver listado de facturas',
    'facturas:editar': 'Editar facturas no autorizadas',
    'facturas:eliminar': 'Eliminar facturas pendientes',
    'facturas:comprobante': 'Ver/descargar comprobantes',

    # Facturadores
    'facturadores:ver': 'Ver facturadores',
    'facturadores:crear': 'Crear facturadores',
    'facturadores:editar': 'Editar facturadores',
    'facturadores:eliminar': 'Eliminar facturadores',
    'facturadores:certificados': 'Gestionar certificados',

    # Receptores
    'receptores:ver': 'Ver receptores',
    'receptores:crear': 'Crear receptores',
    'receptores:editar': 'Editar receptores',
    'receptores:eliminar': 'Eliminar receptores',

    # Consultas ARCA
    'comprobantes:consultar': 'Consultar comprobantes en ARCA',

    # Usuarios (solo admin)
    'usuarios:ver': 'Ver listado de usuarios',
    'usuarios:crear': 'Crear usuarios',
    'usuarios:editar': 'Editar usuarios',
    'usuarios:desactivar': 'Activar/desactivar usuarios',

    # Auditoria (solo admin)
    'auditoria:ver': 'Ver log de auditoria',

    # Email
    'email:configurar': 'Configurar servidor de email',
    'email:enviar': 'Enviar facturas por email',
}

ROLE_PERMISSIONS = {
    'admin': list(PERMISSIONS.keys()),
    'operator': [
        'dashboard:ver',
        'facturar:importar',
        'facturar:ejecutar',
        'facturas:ver',
        'facturas:editar',
        'facturas:eliminar',
        'facturas:comprobante',
        'facturadores:ver',
        'receptores:ver',
        'receptores:crear',
        'receptores:editar',
        'comprobantes:consultar',
        'email:enviar',
    ],
    'viewer': [
        'dashboard:ver',
        'facturas:ver',
        'facturas:comprobante',
        'facturadores:ver',
        'receptores:ver',
        'comprobantes:consultar',
    ],
}

ROLES = {
    'admin': 'Administrador',
    'operator': 'Operador',
    'viewer': 'Solo lectura',
}


def get_user_permissions(rol):
    """Retorna la lista de permisos para un rol dado."""
    return ROLE_PERMISSIONS.get(rol, [])


def has_permission(rol, permission):
    """Verifica si un rol tiene un permiso especifico."""
    return permission in get_user_permissions(rol)
