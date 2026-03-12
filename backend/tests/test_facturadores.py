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
            'ingresos_brutos': '20-98765432-1',
            'fecha_inicio_actividades': '2021-06-15',
            'ambiente': 'testing'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['cuit'] == '20987654321'
        assert data['razon_social'] == 'Nueva SA'
        assert data['punto_venta'] == 2
        assert data['ingresos_brutos'] == '20-98765432-1'
        assert data['fecha_inicio_actividades'] == '2021-06-15'

    def test_create_missing_fields(self, client, auth_headers):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20987654321'
        })
        assert response.status_code == 400

    def test_create_missing_ingresos_brutos(self, client, auth_headers):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20987654321',
            'razon_social': 'Nueva SA',
            'punto_venta': 2,
            'fecha_inicio_actividades': '2021-06-15',
        })
        assert response.status_code == 400
        assert 'ingresos_brutos' in response.get_json()['error']

    def test_create_missing_fecha_inicio(self, client, auth_headers):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20987654321',
            'razon_social': 'Nueva SA',
            'punto_venta': 2,
            'ingresos_brutos': '20-98765432-1',
        })
        assert response.status_code == 400
        assert 'fecha_inicio_actividades' in response.get_json()['error']

    def test_create_duplicate(self, client, auth_headers, facturador):
        response = client.post('/api/facturadores', headers=auth_headers, json={
            'cuit': '20123456789',
            'razon_social': 'Duplicado SA',
            'punto_venta': 1,
            'ingresos_brutos': '20-12345678-9',
            'fecha_inicio_actividades': '2020-01-01',
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

    def test_update_ingresos_brutos(self, client, auth_headers, facturador):
        response = client.put(
            f'/api/facturadores/{facturador.id}',
            headers=auth_headers,
            json={
                'ingresos_brutos': '30-99999999-0',
                'fecha_inicio_actividades': '2022-03-10',
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ingresos_brutos'] == '30-99999999-0'
        assert data['fecha_inicio_actividades'] == '2022-03-10'

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
