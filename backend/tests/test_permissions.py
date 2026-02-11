from app.services.permissions import (
    PERMISSIONS, ROLE_PERMISSIONS, ROLES,
    get_user_permissions, has_permission
)


class TestPermissions:
    def test_admin_has_all_permissions(self):
        admin_perms = get_user_permissions('admin')
        assert set(admin_perms) == set(PERMISSIONS.keys())

    def test_operator_can_facturar(self):
        assert has_permission('operator', 'facturar:importar')
        assert has_permission('operator', 'facturar:ejecutar')
        assert has_permission('operator', 'facturas:ver')

    def test_operator_cannot_manage_users(self):
        assert not has_permission('operator', 'usuarios:ver')
        assert not has_permission('operator', 'usuarios:crear')
        assert not has_permission('operator', 'usuarios:editar')
        assert not has_permission('operator', 'usuarios:desactivar')

    def test_operator_cannot_manage_facturadores(self):
        assert not has_permission('operator', 'facturadores:crear')
        assert not has_permission('operator', 'facturadores:editar')
        assert not has_permission('operator', 'facturadores:eliminar')
        assert not has_permission('operator', 'facturadores:certificados')

    def test_viewer_readonly(self):
        assert has_permission('viewer', 'dashboard:ver')
        assert has_permission('viewer', 'facturas:ver')
        assert has_permission('viewer', 'facturadores:ver')
        assert has_permission('viewer', 'receptores:ver')
        assert has_permission('viewer', 'comprobantes:consultar')

    def test_viewer_cannot_write(self):
        assert not has_permission('viewer', 'facturar:importar')
        assert not has_permission('viewer', 'facturar:ejecutar')
        assert not has_permission('viewer', 'facturas:eliminar')
        assert not has_permission('viewer', 'receptores:crear')
        assert not has_permission('viewer', 'usuarios:ver')

    def test_unknown_role_has_no_permissions(self):
        assert get_user_permissions('nonexistent') == []
        assert not has_permission('nonexistent', 'dashboard:ver')

    def test_all_roles_defined(self):
        assert 'admin' in ROLES
        assert 'operator' in ROLES
        assert 'viewer' in ROLES

    def test_role_permissions_only_use_valid_permissions(self):
        valid = set(PERMISSIONS.keys())
        for rol, perms in ROLE_PERMISSIONS.items():
            for perm in perms:
                assert perm in valid, f"Permiso '{perm}' en rol '{rol}' no esta definido en PERMISSIONS"
