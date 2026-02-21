import io
from uuid import UUID
from app.models import Factura, Facturador, Lote


class TestListLotes:
    def test_list_empty(self, client, auth_headers):
        response = client.get('/api/lotes', headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['items'] == []

    def test_list_after_import(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Lote Test',
            'tipo': 'factura'
        }
        client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )

        response = client.get('/api/lotes', headers=auth_headers)
        assert response.status_code == 200
        items = response.get_json()['items']
        assert len(items) == 1
        assert items[0]['etiqueta'] == 'Lote Test'
        assert items[0]['total_facturas'] == 1

    def test_list_lotes_para_facturar_includes_completed_with_error(self, client, auth_headers, facturador, receptor, db):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote reintento visible',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = UUID(import_response.get_json()['lote']['id'])

        lote = Lote.query.filter_by(id=lote_id).first()
        factura = Factura.query.filter_by(lote_id=lote_id).first()
        lote.estado = 'completado'
        factura.estado = 'error'
        factura.error_codigo = '100'
        factura.error_mensaje = 'Error de prueba'
        db.session.commit()

        response = client.get('/api/lotes?para_facturar=true', headers=auth_headers)
        assert response.status_code == 200
        ids = [item['id'] for item in response.get_json()['items']]
        assert str(lote_id) in ids

    def test_list_lotes_para_facturar_excludes_completed_without_retryables(self, client, auth_headers, facturador, receptor, db):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote no reintetable',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = UUID(import_response.get_json()['lote']['id'])

        lote = Lote.query.filter_by(id=lote_id).first()
        factura = Factura.query.filter_by(lote_id=lote_id).first()
        lote.estado = 'completado'
        factura.estado = 'autorizado'
        db.session.commit()

        response = client.get('/api/lotes?para_facturar=true', headers=auth_headers)
        assert response.status_code == 200
        ids = [item['id'] for item in response.get_json()['items']]
        assert str(lote_id) not in ids


class TestGetLote:
    def test_get_with_stats(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-16,2000.00,1652.89"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Lote stats',
            'tipo': 'factura'
        }
        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        lote_id = import_response.get_json()['lote']['id']

        response = client.get(f'/api/lotes/{lote_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_facturas'] == 2
        assert 'stats' in data
        assert data['stats']['pendientes'] == 2

    def test_get_not_found(self, client, auth_headers):
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f'/api/lotes/{fake_id}', headers=auth_headers)
        assert response.status_code == 404


class TestDeleteLote:
    def test_delete_lote_without_autorizadas(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Lote delete',
            'tipo': 'factura'
        }
        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        lote_id = import_response.get_json()['lote']['id']

        response = client.delete(f'/api/lotes/{lote_id}', headers=auth_headers)
        assert response.status_code == 200

        # Verify lote was deleted
        response = client.get(f'/api/lotes/{lote_id}', headers=auth_headers)
        assert response.status_code == 404


class TestFacturarLote:
    def test_facturar_lote_allows_switching_facturador(self, client, auth_headers, facturador, receptor, db, monkeypatch):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote facturar switch',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = import_response.get_json()['lote']['id']

        alt_facturador = Facturador(
            tenant_id=facturador.tenant_id,
            cuit='20333444556',
            razon_social='Facturador Alternativo',
            punto_venta=9,
            ambiente='testing',
            activo=True,
            cert_encrypted=b'cert',
            key_encrypted=b'key',
        )
        db.session.add(alt_facturador)
        db.session.commit()

        class _Task:
            id = 'task-test-1'

        def _fake_delay(*_args, **_kwargs):
            return _Task()

        monkeypatch.setattr('app.tasks.facturacion.procesar_lote.delay', _fake_delay)

        response = client.post(
            f'/api/lotes/{lote_id}/facturar',
            headers=auth_headers,
            json={'facturador_id': str(alt_facturador.id)}
        )
        assert response.status_code == 202
        payload = response.get_json()
        assert payload['facturador']['id'] == str(alt_facturador.id)

        factura = Factura.query.filter_by(lote_id=UUID(lote_id)).first()
        assert str(factura.facturador_id) == str(alt_facturador.id)
        assert factura.punto_venta == alt_facturador.punto_venta

    def test_facturar_lote_rejects_facturador_without_certificates(self, client, auth_headers, facturador, receptor, db):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote sin cert',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = import_response.get_json()['lote']['id']

        alt_facturador = Facturador(
            tenant_id=facturador.tenant_id,
            cuit='20333444557',
            razon_social='Facturador sin certificados',
            punto_venta=10,
            ambiente='testing',
            activo=True,
        )
        db.session.add(alt_facturador)
        db.session.commit()

        response = client.post(
            f'/api/lotes/{lote_id}/facturar',
            headers=auth_headers,
            json={'facturador_id': str(alt_facturador.id)}
        )
        assert response.status_code == 400
        assert 'no tiene certificados' in response.get_json()['error'].lower()

    def test_facturar_lote_retries_error_facturas_by_resetting_to_pending(self, client, auth_headers, facturador, receptor, db, monkeypatch):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote reintento',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = UUID(import_response.get_json()['lote']['id'])

        lote = Lote.query.filter_by(id=lote_id).first()
        factura = Factura.query.filter_by(lote_id=lote_id).first()
        lote.estado = 'completado'
        factura.estado = 'error'
        factura.error_codigo = 'E01'
        factura.error_mensaje = 'Error ARCA'
        db.session.commit()

        facturador_con_cert = Facturador(
            tenant_id=facturador.tenant_id,
            cuit='20333444558',
            razon_social='Facturador Reintento',
            punto_venta=11,
            ambiente='testing',
            activo=True,
            cert_encrypted=b'cert',
            key_encrypted=b'key',
        )
        db.session.add(facturador_con_cert)
        db.session.commit()

        class _Task:
            id = 'task-test-retry'

        def _fake_delay(*_args, **_kwargs):
            return _Task()

        monkeypatch.setattr('app.tasks.facturacion.procesar_lote.delay', _fake_delay)

        response = client.post(
            f'/api/lotes/{lote_id}/facturar',
            headers=auth_headers,
            json={'facturador_id': str(facturador_con_cert.id)}
        )
        assert response.status_code == 202

        db.session.refresh(factura)
        assert factura.estado == 'pendiente'
        assert factura.error_codigo is None
        assert factura.error_mensaje is None

    def test_facturar_lote_returns_400_when_only_autorizadas(self, client, auth_headers, facturador, receptor, db):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,1000.00,826.45"""

        import_response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data={
                'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
                'etiqueta': 'Lote autorizado',
                'tipo': 'factura',
            },
            content_type='multipart/form-data'
        )
        assert import_response.status_code == 201
        lote_id = UUID(import_response.get_json()['lote']['id'])

        lote = Lote.query.filter_by(id=lote_id).first()
        factura = Factura.query.filter_by(lote_id=lote_id).first()
        lote.estado = 'completado'
        factura.estado = 'autorizado'
        db.session.commit()

        response = client.post(
            f'/api/lotes/{lote_id}/facturar',
            headers=auth_headers,
            json={'facturador_id': str(facturador.id)}
        )
        assert response.status_code == 400
        assert 'no hay facturas pendientes o con error' in response.get_json()['error'].lower()
