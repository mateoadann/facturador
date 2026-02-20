import pytest
import io
from datetime import date
from decimal import Decimal
from app.models import Receptor, Tenant, Usuario, Factura


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

    def test_update_doc_nro_success(self, client, auth_headers, receptor):
        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-22222222-2'}
        )
        assert response.status_code == 200
        assert response.get_json()['doc_nro'] == '30222222222'

    def test_update_doc_nro_invalid_format(self, client, auth_headers, receptor):
        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-abc'}
        )
        assert response.status_code == 400
        assert response.get_json()['error'] == 'CUIT/CUIL inválido'

    def test_update_doc_nro_rejects_duplicate_same_tenant(self, client, auth_headers, receptor, db):
        another = Receptor(
            tenant_id=receptor.tenant_id,
            doc_tipo=80,
            doc_nro='30222222222',
            razon_social='Otro Receptor',
            activo=True
        )
        db.session.add(another)
        db.session.commit()

        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-22222222-2'}
        )
        assert response.status_code == 400
        assert response.get_json()['error'] == 'Ya existe un receptor con ese documento'

    def test_update_doc_nro_same_value_ok(self, client, auth_headers, receptor):
        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-11111111-1'}
        )
        assert response.status_code == 200
        assert response.get_json()['doc_nro'] == '30111111111'

    def test_update_doc_nro_blocked_if_has_factura_autorizada(self, client, auth_headers, receptor, facturador, db):
        factura = Factura(
            tenant_id=receptor.tenant_id,
            facturador_id=facturador.id,
            receptor_id=receptor.id,
            tipo_comprobante=1,
            concepto=1,
            punto_venta=1,
            fecha_emision=date(2026, 1, 15),
            importe_total=Decimal('121.00'),
            importe_neto=Decimal('100.00'),
            importe_iva=Decimal('21.00'),
            estado='autorizado'
        )
        db.session.add(factura)
        db.session.commit()

        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-33333333-3'}
        )
        assert response.status_code == 400
        assert response.get_json()['error'] == 'No se puede modificar el CUIT de un receptor con facturas autorizadas'

    def test_update_doc_nro_allows_duplicate_in_other_tenant(self, client, auth_headers, receptor, db):
        other_tenant = Tenant(nombre='Other Tenant CUIT', slug='other-tenant-cuit', activo=True)
        db.session.add(other_tenant)
        db.session.flush()

        other_receptor = Receptor(
            tenant_id=other_tenant.id,
            doc_tipo=80,
            doc_nro='30444444444',
            razon_social='Otro Tenant',
            activo=True
        )
        db.session.add(other_receptor)
        db.session.commit()

        response = client.put(
            f'/api/receptores/{receptor.id}',
            headers=auth_headers,
            json={'doc_nro': '30-44444444-4'}
        )
        assert response.status_code == 200
        assert response.get_json()['doc_nro'] == '30444444444'


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


class TestImportReceptores:
    def test_import_receptores_success_creates_new(self, client, auth_headers):
        csv_content = """cuit,razon_social,condicion_iva,email,direccion
30-12345678-9,Cliente Uno SA,IVA Responsable Inscripto,uno@test.com,Calle 123
30123456780,Cliente Dos SRL,Consumidor Final,dos@test.com,Avenida 456
"""
        response = client.post(
            '/api/receptores/import',
            headers=auth_headers,
            data={'file': (io.BytesIO(csv_content.encode('utf-8')), 'receptores.csv')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['procesados'] == 2
        assert data['creados'] == 2
        assert data['actualizados'] == 0
        assert data['omitidos'] == 0
        assert data['errores'] == []

    def test_import_receptores_upsert_updates_existing(self, client, auth_headers, receptor):
        csv_content = """doc nro,razón social,condicion iva,email,dirección
30-11111111-1,Receptor Actualizado SA,Consumidor Final,actualizado@test.com,Nueva 999
"""
        response = client.post(
            '/api/receptores/import',
            headers=auth_headers,
            data={'file': (io.BytesIO(csv_content.encode('utf-8')), 'receptores.csv')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['creados'] == 0
        assert data['actualizados'] == 1

        updated = client.get(f'/api/receptores/{receptor.id}', headers=auth_headers).get_json()
        assert updated['razon_social'] == 'Receptor Actualizado SA'
        assert updated['condicion_iva'] == 'Consumidor Final'
        assert updated['email'] == 'actualizado@test.com'
        assert updated['direccion'] == 'Nueva 999'

    def test_import_receptores_partial_with_invalid_rows(self, client, auth_headers):
        csv_content = """cuit,razon_social,email
30123456781,Valido SA,valido@test.com
30-abc,CUIT Invalido SA,invalido@test.com
30123456782,,sinrazon@test.com
30123456783,Email Invalido SA,mail-invalido
"""
        response = client.post(
            '/api/receptores/import',
            headers=auth_headers,
            data={'file': (io.BytesIO(csv_content.encode('utf-8')), 'receptores.csv')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['procesados'] == 4
        assert data['creados'] == 1
        assert data['actualizados'] == 0
        assert data['omitidos'] == 3
        assert len(data['errores']) == 3

    def test_import_receptores_requires_file(self, client, auth_headers):
        response = client.post('/api/receptores/import', headers=auth_headers)
        assert response.status_code == 400

    def test_import_receptores_permission_denied_for_viewer(self, client, viewer_headers):
        csv_content = "cuit,razon_social\n30123456789,Viewer Bloqueado SA\n"
        response = client.post(
            '/api/receptores/import',
            headers=viewer_headers,
            data={'file': (io.BytesIO(csv_content.encode('utf-8')), 'receptores.csv')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 403

    def test_import_receptores_tenant_isolation(self, client, auth_headers, db):
        other_tenant = Tenant(nombre='Other Tenant', slug='other-tenant', activo=True)
        db.session.add(other_tenant)
        db.session.flush()

        other_user = Usuario(
            tenant_id=other_tenant.id,
            email='other-admin@test.com',
            nombre='Other Admin',
            rol='admin',
            activo=True
        )
        other_user.set_password('test123')
        db.session.add(other_user)

        other_receptor = Receptor(
            tenant_id=other_tenant.id,
            doc_tipo=80,
            doc_nro='30555555555',
            razon_social='Otro Tenant SA',
            condicion_iva='IVA Responsable Inscripto',
            email='other@test.com',
            direccion='Otra calle 1',
            activo=True
        )
        db.session.add(other_receptor)
        db.session.commit()

        csv_content = """cuit,razon_social,condicion_iva,email,direccion
30-55555555-5,Mi Tenant SA,Consumidor Final,mio@test.com,Mi calle 2
"""
        response = client.post(
            '/api/receptores/import',
            headers=auth_headers,
            data={'file': (io.BytesIO(csv_content.encode('utf-8')), 'receptores.csv')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        assert response.get_json()['creados'] == 1
        assert response.get_json()['actualizados'] == 0

        persisted_other = Receptor.query.filter_by(id=other_receptor.id).first()
        assert persisted_other.razon_social == 'Otro Tenant SA'
        assert persisted_other.email == 'other@test.com'
