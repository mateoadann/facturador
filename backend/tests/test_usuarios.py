import pytest


class TestListUsuarios:
    def test_admin_can_list(self, client, auth_headers):
        response = client.get('/api/usuarios', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert data['total'] >= 1

    def test_operator_cannot_list(self, client, operator_headers):
        response = client.get('/api/usuarios', headers=operator_headers)
        assert response.status_code == 403

    def test_viewer_cannot_list(self, client, viewer_headers):
        response = client.get('/api/usuarios', headers=viewer_headers)
        assert response.status_code == 403

    def test_unauthenticated(self, client, tenant):
        response = client.get('/api/usuarios')
        assert response.status_code == 401


class TestCreateUsuario:
    def test_create_success(self, client, auth_headers):
        response = client.post('/api/usuarios', headers=auth_headers, json={
            'email': 'new@test.com',
            'password': 'password123',
            'nombre': 'Nuevo Usuario',
            'rol': 'operator'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['email'] == 'new@test.com'
        assert data['rol'] == 'operator'

    def test_create_duplicate_email(self, client, auth_headers, operator_user):
        response = client.post('/api/usuarios', headers=auth_headers, json={
            'email': 'operator@test.com',
            'password': 'password123',
            'nombre': 'Duplicado',
            'rol': 'operator'
        })
        assert response.status_code == 400
        assert 'ya existe' in response.get_json()['error'].lower()

    def test_create_short_password(self, client, auth_headers):
        response = client.post('/api/usuarios', headers=auth_headers, json={
            'email': 'short@test.com',
            'password': '123',
            'nombre': 'Short Pass',
            'rol': 'operator'
        })
        assert response.status_code == 400
        assert '8 caracteres' in response.get_json()['error']

    def test_create_invalid_rol(self, client, auth_headers):
        response = client.post('/api/usuarios', headers=auth_headers, json={
            'email': 'invalid@test.com',
            'password': 'password123',
            'nombre': 'Invalid Rol',
            'rol': 'superadmin'
        })
        assert response.status_code == 400

    def test_operator_cannot_create(self, client, operator_headers):
        response = client.post('/api/usuarios', headers=operator_headers, json={
            'email': 'forbidden@test.com',
            'password': 'password123',
            'nombre': 'Forbidden',
            'rol': 'operator'
        })
        assert response.status_code == 403


class TestUpdateUsuario:
    def test_update_nombre(self, client, auth_headers, operator_user):
        response = client.put(
            f'/api/usuarios/{operator_user.id}',
            headers=auth_headers,
            json={'nombre': 'Nombre Actualizado'}
        )
        assert response.status_code == 200
        assert response.get_json()['nombre'] == 'Nombre Actualizado'

    def test_cannot_change_own_rol(self, client, auth_headers, admin_user):
        response = client.put(
            f'/api/usuarios/{admin_user.id}',
            headers=auth_headers,
            json={'rol': 'operator'}
        )
        assert response.status_code == 400

    def test_update_not_found(self, client, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.put(
            f'/api/usuarios/{fake_id}',
            headers=auth_headers,
            json={'nombre': 'No existe'}
        )
        assert response.status_code == 404


class TestToggleActive:
    def test_toggle_deactivate(self, client, auth_headers, operator_user):
        response = client.post(
            f'/api/usuarios/{operator_user.id}/toggle-active',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()['activo'] is False

    def test_toggle_reactivate(self, client, auth_headers, operator_user):
        # Desactivar
        client.post(
            f'/api/usuarios/{operator_user.id}/toggle-active',
            headers=auth_headers
        )
        # Reactivar
        response = client.post(
            f'/api/usuarios/{operator_user.id}/toggle-active',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()['activo'] is True

    def test_cannot_deactivate_self(self, client, auth_headers, admin_user):
        response = client.post(
            f'/api/usuarios/{admin_user.id}/toggle-active',
            headers=auth_headers
        )
        assert response.status_code == 400


class TestLoginRateLimiting:
    def test_lockout_after_failed_attempts(self, client, admin_user):
        for i in range(5):
            response = client.post('/api/auth/login', json={
                'email': 'admin@test.com',
                'password': 'wrongpassword'
            })
            assert response.status_code == 401

        # 6th attempt should be locked
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 429
        assert 'bloqueada' in response.get_json()['error'].lower()

    def test_successful_login_resets_attempts(self, client, admin_user):
        # 3 failed attempts
        for i in range(3):
            client.post('/api/auth/login', json={
                'email': 'admin@test.com',
                'password': 'wrongpassword'
            })

        # Successful login
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'test123'
        })
        assert response.status_code == 200

        # Should be able to fail again without lockout
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401


class TestChangePassword:
    def test_change_password_success(self, client, auth_headers):
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'test123',
            'new_password': 'newpassword123'
        })
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123'
        })
        assert response.status_code == 401

    def test_change_password_too_short(self, client, auth_headers):
        response = client.post('/api/auth/change-password', headers=auth_headers, json={
            'current_password': 'test123',
            'new_password': '123'
        })
        assert response.status_code == 400


class TestLoginIncludesPermissions:
    def test_login_returns_permisos(self, client, admin_user):
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'test123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'permisos' in data['user']
        assert 'dashboard:ver' in data['user']['permisos']

    def test_me_returns_permisos(self, client, auth_headers):
        response = client.get('/api/auth/me', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'permisos' in data['user']


class TestRolesEndpoint:
    def test_list_roles(self, client, auth_headers):
        response = client.get('/api/usuarios/roles', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'admin' in data['roles']
        assert 'operator' in data['roles']
        assert 'viewer' in data['roles']
