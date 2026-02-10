import pytest


class TestListFacturadores:
    def test_list_empty(self, client, auth_headers):
        response = client.get('/api/facturadores', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['items'] == []
        assert data['total'] == 0

    def test_list_with_data(self, client, auth_headers, facturador):
        response = client.get('/api/facturadores', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['items']) == 1
        assert data['items'][0]['cuit'] == '20123456789'

    def test_list_unauthenticated(self, client, db):
        response = client.get('/api/facturadores')
        assert response.status_code == 401


class TestCreateFacturador:
    def test_create_success(self, client, auth_headers):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20987654321',
            'razon_social': 'Nueva SA',
            'punto_venta': 2,
            'condicion_iva': 'IVA Responsable Inscripto',
            'ambiente': 'testing'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['cuit'] == '20987654321'
        assert data['razon_social'] == 'Nueva SA'
        assert data['punto_venta'] == 2

    def test_create_missing_fields(self, client, auth_headers):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20987654321'
        })
        assert response.status_code == 400

    def test_create_duplicate(self, client, auth_headers, facturador):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20123456789',
            'razon_social': 'Duplicado SA',
            'punto_venta': 1
        })
        assert response.status_code == 400
        assert 'Ya existe' in response.get_json()['error']


class TestUpdateFacturador:
    def test_update_success(self, client, auth_headers, facturador):
        response = client.put(
            f'/api/facturadores/{facturador.id}',
            headers=auth_headers,
            json={'razon_social': 'Updated SA'}
        )
        assert response.status_code == 200
        assert response.get_json()['razon_social'] == 'Updated SA'

    def test_update_not_found(self, client, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.put(
            f'/api/facturadores/{fake_id}',
            headers=auth_headers,
            json={'razon_social': 'X'}
        )
        assert response.status_code == 404


class TestDeleteFacturador:
    def test_delete_soft(self, client, auth_headers, facturador):
        response = client.delete(
            f'/api/facturadores/{facturador.id}',
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify soft delete
        get_response = client.get(
            f'/api/facturadores/{facturador.id}',
            headers=auth_headers
        )
        assert get_response.get_json()['activo'] is False
