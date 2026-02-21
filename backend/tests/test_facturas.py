import io
import pytest
from uuid import UUID
from app.models import Lote, Factura, Receptor


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
            'etiqueta': 'Test CSV inválido',
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

    def test_import_tipo_c_normalizes_iva_to_zero(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva
{facturador.cuit},{receptor.doc_nro},11,1,2026-01-15,12100.00,10000.00,2100.00"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'facturas-c.csv'),
            'etiqueta': 'Test Import tipo C',
            'tipo': 'factura'
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        factura = Factura.query.first()
        assert factura is not None
        assert factura.tipo_comprobante == 11
        assert float(factura.importe_neto) == 10000.0
        assert float(factura.importe_iva) == 0.0
        assert float(factura.importe_total) == 10000.0


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

    def test_list_with_multiple_estados_filter(self, client, auth_headers, facturador, receptor):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,12100.00,10000.00"""

        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'etiqueta': 'Test estados multiple',
            'tipo': 'factura'
        }
        client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )

        response = client.get('/api/facturas?estados=pendiente,borrador', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 1

        response = client.get('/api/facturas?estados=autorizado,error', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.get_json()['items']) == 0

    def test_list_with_invalid_estados_filter(self, client, auth_headers):
        response = client.get('/api/facturas?estados=autorizado,invalido', headers=auth_headers)
        assert response.status_code == 400
        assert 'Estados inválidos' in response.get_json()['error']


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


class TestUpdateFactura:
    def _create_factura(self, client, auth_headers, facturador, receptor, etiqueta='Test editar factura'):
        csv_content = f"""facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
{facturador.cuit},{receptor.doc_nro},1,1,2026-01-15,12100.00,10000.00"""
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'facturas.csv'),
            'etiqueta': etiqueta,
            'tipo': 'factura'
        }
        response = client.post(
            '/api/facturas/import',
            headers=auth_headers,
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 201
        factura_id = client.get('/api/facturas', headers=auth_headers).get_json()['items'][0]['id']
        return factura_id

    def test_update_factura_pending_success(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-pending')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'importe_total': 15000.00,
                'importe_neto': 12000.00,
                'importe_iva': 3000.00,
            }
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['importe_total'] == 15000.0
        assert payload['importe_neto'] == 12000.0
        assert payload['importe_iva'] == 3000.0

    def test_update_factura_error_moves_to_pending(self, client, auth_headers, facturador, receptor, db):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-error')
        factura = Factura.query.filter_by(id=UUID(factura_id)).first()
        assert factura is not None
        factura.estado = 'error'
        factura.error_codigo = 'X1'
        factura.error_mensaje = 'fallo'
        db.session.commit()

        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={'importe_total': 13000.00}
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['estado'] == 'pendiente'
        assert payload['error_codigo'] is None
        assert payload['error_mensaje'] is None

    def test_update_factura_autorizada_rejected(self, client, auth_headers, facturador, receptor, db):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-autorizada')
        factura = Factura.query.filter_by(id=UUID(factura_id)).first()
        assert factura is not None
        factura.estado = 'autorizado'
        db.session.commit()

        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={'importe_total': 9999.00}
        )
        assert response.status_code == 400
        assert 'autorizada' in response.get_json()['error']

    def test_update_factura_concepto_2_requires_dates(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-concepto-2')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'concepto': 2,
                'fecha_desde': None,
                'fecha_hasta': None,
                'fecha_vto_pago': None,
            }
        )
        assert response.status_code == 400
        assert 'fecha_desde' in response.get_json()['error']

    def test_update_factura_nota_requires_cbte_asoc(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-nota')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'tipo_comprobante': 3,
                'cbte_asoc_tipo': None,
                'cbte_asoc_pto_vta': None,
                'cbte_asoc_nro': None,
            }
        )
        assert response.status_code == 400
        assert 'cbte_asoc' in response.get_json()['error']

    def test_update_factura_rejects_other_tenant_receptor(self, client, auth_headers, facturador, receptor, db, tenant):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-tenant')
        from app.models import Tenant
        other_tenant = Tenant(
            nombre='Tenant externo',
            slug='tenant-externo',
            activo=True
        )
        db.session.add(other_tenant)
        db.session.flush()

        other_receptor = Receptor(
            tenant_id=other_tenant.id,
            doc_tipo=80,
            doc_nro='30222222222',
            razon_social='Otro tenant receptor',
            activo=True
        )
        db.session.add(other_receptor)
        db.session.commit()

        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={'receptor_id': str(other_receptor.id)}
        )
        assert response.status_code == 400
        assert 'Receptor inválido' == response.get_json()['error']

    def test_update_factura_recalculates_totals_from_items(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-items-recalc')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'items': [
                    {
                        'descripcion': 'Servicio base',
                        'cantidad': 2,
                        'precio_unitario': 1000.00,
                        'alicuota_iva_id': 5,
                    },
                    {
                        'descripcion': 'Producto sin IVA',
                        'cantidad': 1,
                        'precio_unitario': 500.00,
                        'alicuota_iva_id': 3,
                    },
                ],
            }
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['importe_neto'] == 2500.0
        assert payload['importe_iva'] == 420.0
        assert payload['importe_total'] == 2920.0

    def test_update_factura_viewer_denied(self, client, viewer_headers, facturador, receptor, auth_headers):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-viewer')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=viewer_headers,
            json={'importe_total': 15000.00}
        )
        assert response.status_code == 403

    def test_update_factura_tipo_c_normalizes_iva_and_total(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-tipo-c')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'tipo_comprobante': 11,
                'importe_neto': 10000.00,
                'importe_iva': 2100.00,
                'importe_total': 12100.00,
            }
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['tipo_comprobante'] == 11
        assert payload['importe_neto'] == 10000.0
        assert payload['importe_iva'] == 0.0
        assert payload['importe_total'] == 10000.0

    def test_update_factura_tipo_c_with_items_forces_zero_iva(self, client, auth_headers, facturador, receptor):
        factura_id = self._create_factura(client, auth_headers, facturador, receptor, etiqueta='editar-tipo-c-items')
        response = client.put(
            f'/api/facturas/{factura_id}',
            headers=auth_headers,
            json={
                'tipo_comprobante': 11,
                'items': [
                    {
                        'descripcion': 'Servicio',
                        'cantidad': 1,
                        'precio_unitario': 1000.00,
                        'alicuota_iva_id': 5,
                    },
                ],
            }
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['tipo_comprobante'] == 11
        assert payload['importe_neto'] == 1000.0
        assert payload['importe_iva'] == 0.0
        assert payload['importe_total'] == 1000.0
