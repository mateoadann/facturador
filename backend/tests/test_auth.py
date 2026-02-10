import pytest


class TestLogin:
    def test_login_success(self, client, admin_user):
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'test123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['email'] == 'admin@test.com'
        assert data['tenant']['slug'] == 'test-tenant'

    def test_login_wrong_password(self, client, admin_user):
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'wrong'
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        response = client.post('/api/auth/login', json={
            'email': 'nobody@test.com',
            'password': 'test123'
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client, db):
        response = client.post('/api/auth/login', json={
            'email': 'admin@test.com'
        })
        assert response.status_code == 400

    def test_login_inactive_user(self, client, db, tenant):
        from app.models import Usuario
        user = Usuario(
            tenant_id=tenant.id,
            email='inactive@test.com',
            nombre='Inactive',
            activo=False
        )
        user.set_password('test123')
        db.session.add(user)
        db.session.commit()

        response = client.post('/api/auth/login', json={
            'email': 'inactive@test.com',
            'password': 'test123'
        })
        assert response.status_code == 403


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        response = client.get('/api/auth/me', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['email'] == 'admin@test.com'
        assert data['tenant']['slug'] == 'test-tenant'

    def test_me_unauthenticated(self, client, db):
        response = client.get('/api/auth/me')
        assert response.status_code == 401


class TestRefresh:
    def test_refresh_token(self, client, admin_user):
        # First login
        login_response = client.post('/api/auth/login', json={
            'email': 'admin@test.com',
            'password': 'test123'
        })
        refresh_token = login_response.get_json()['refresh_token']

        # Refresh
        response = client.post('/api/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })
        assert response.status_code == 200
        assert 'access_token' in response.get_json()


class TestLogout:
    def test_logout(self, client, auth_headers):
        response = client.post('/api/auth/logout', headers=auth_headers)
        assert response.status_code == 200
