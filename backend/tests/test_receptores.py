import pytest


class TestListReceptores:
    def test_list_empty(self, client, auth_headers):
        response = client.get('/api/receptores', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['items'] == []

    def test_list_with_data(self, client, auth_headers, receptor):
        response = client.get('/api/receptores', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['items']) == 1
        assert data['items'][0]['doc_nro'] == '30111111111'

    def test_list_with_search(self, client, auth_headers, receptor):
        response = client.get('/api/receptores?search=Receptor', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 1

        response = client.get('/api/receptores?search=inexistente', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 0


class TestCreateReceptor:
    def test_create_success(self, client, auth_headers):
        response = client.post('/api/receptores', headers=auth_headers, json={
            'doc_nro': '30-99999999-1',
            'razon_social': 'Nuevo Receptor SA',
            'condicion_iva': 'Consumidor Final'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['doc_nro'] == '30999999991'  # Cleaned
        assert data['razon_social'] == 'Nuevo Receptor SA'

    def test_create_missing_razon_social(self, client, auth_headers):
        response = client.post('/api/receptores', headers=auth_headers, json={
            'doc_nro': '30999999991'
        })
        assert response.status_code == 400

    def test_create_duplicate_doc_nro(self, client, auth_headers, receptor):
        response = client.post('/api/receptores', headers=auth_headers, json={
            'doc_nro': '30111111111',
            'razon_social': 'Duplicado'
        })
        assert response.status_code == 400


class TestUpdateReceptor:
    def test_update_success(self, client, auth_headers, receptor):
        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'email': 'nuevo@email.com'}
        )
        assert response.status_code == 200
        assert response.get_json()['email'] == 'nuevo@email.com'


class TestDeleteReceptor:
    def test_delete_soft(self, client, auth_headers, receptor):
        response = client.delete(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers
        )
        assert response.status_code == 200

        get_response = client.get(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers
        )
        assert get_response.get_json()['activo'] is False
