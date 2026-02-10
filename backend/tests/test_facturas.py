import io
import pytest
from app.models import Lote


class TestImportCSV:
    def test_import_success(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,12100.00,10000.00
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-16,24200.00,20000.00"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'facturas.csv'),
            'etiqueta': 'Test Import',
            'tipo': 'factura'
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        result = response.get_json()
        assert result['facturas_importadas'] == 2
        assert result['lote']['etiqueta'] == 'Test Import'
        assert result['lote']['total_facturas'] == 2

    def test_import_no_file(self, client, auth_headers):
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_import_invalid_csv(self, client, auth_headers):
        csv_content = "col1,col2\nval1,val2"
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'bad.csv'),
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        assert 'Columnas requeridas faltantes' in str(response.get_json())

    def test_import_nonexistent_facturador(self, client, auth_headers, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
99999999999,{receptor.doc_nro},1,1,2026-01-15,12100.00,10000.00"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'facturas.csv'),
            'etiqueta': 'Test Import inexistente',
            'tipo': 'factura'
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        result = response.get_json()
        assert len(result['errores_creacion']) > 0

    def test_import_auto_creates_receptor(self, client, auth_headers, facturador):
        """Si el receptor no existe, se crea automáticamente."""
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},30999888777,1,1,2026-01-15,5000.00,4132.23"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'facturas.csv'),
            'etiqueta': 'Test Import auto receptor',
            'tipo': 'factura'
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        assert response.get_json()['facturas_importadas'] == 1


class TestListFacturas:
    def test_list_empty(self, client, auth_headers):
        response = client.get('/api/facturas', headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['items'] == []

    def test_list_with_filters(self, client, auth_headers, facturador, receptor):
        # First import some data
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,12100.00,10000.00"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Test filtros',
            'tipo': 'factura'
        }
        client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )

        # Filter by estado
        response = client.get('/api/facturas?estado=pendiente', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 1

        response = client.get('/api/facturas?estado=autorizado', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 0


class TestBulkDeleteFacturas:
    def test_bulk_delete(self, client, auth_headers, facturador, receptor):
        # Import first
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-16,2000.00,1652.89"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Test bulk delete',
            'tipo': 'factura'
        }
        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )

        # Get factura IDs
        list_response = client.get('/api/facturas', headers=auth_headers)
        ids = [f['id'] for f in list_response.get_json()['items']]

        # Bulk delete
        response = client.delete('/api/facturas', headers=auth_headers, json={'ids': ids})
        assert response.status_code == 200
        assert response.get_json()['deleted'] == 2

    def test_bulk_delete_no_ids(self, client, auth_headers):
        response = client.delete('/api/facturas', headers=auth_headers, json={})
        assert response.status_code == 400

    def test_bulk_delete_removes_empty_lote(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Lote para borrar',
            'tipo': 'factura'
        }
        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = import_response.get_json()['lote']['id']

        list_response = client.get('/api/facturas', headers=auth_headers)
        ids = [f['id'] for f in list_response.get_json()['items']]

        response = client.delete('/api/facturas', headers=auth_headers, json={'ids': ids})
        assert response.status_code == 200
        payload = response.get_json()
        assert lote_id in payload.get('deleted_lote_ids', [])

        lotes_response = client.get('/api/lotes?estado=pendiente', headers=auth_headers)
        assert lotes_response.status_code == 200
        assert all(l['id'] != lote_id for l in lotes_response.get_json()['items'])

    def test_can_reuse_label_after_lote_is_emptied(self, client, auth_headers, facturador, receptor):
        etiqueta = 'Etiqueta reutilizable'
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        first_import = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'first.csv'),
                'etiqueta': etiqueta,
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert first_import.status_code == 201

        list_response = client.get('/api/facturas', headers=auth_headers)
        ids = [f['id'] for f in list_response.get_json()['items']]
        delete_response = client.delete('/api/facturas', headers=auth_headers, json={'ids': ids})
        assert delete_response.status_code == 200

        second_import = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'second.csv'),
                'etiqueta': etiqueta,
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert second_import.status_code == 201

        lotes = Lote.query.filter_by(etiqueta=etiqueta).all()
        assert len(lotes) == 1
