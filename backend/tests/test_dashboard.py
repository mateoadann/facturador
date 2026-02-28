from datetime import date
from decimal import Decimal

from app.models import Factura, Facturador, Receptor, Tenant


def _create_factura(db, tenant_id, facturador_id, receptor_id, fecha_emision, importe_total, estado='autorizado'):
    factura = Factura(
        tenant_id=tenant_id,
        facturador_id=facturador_id,
        receptor_id=receptor_id,
        tipo_comprobante=1,
        concepto=1,
        punto_venta=1,
        fecha_emision=fecha_emision,
        importe_total=Decimal(str(importe_total)),
        importe_neto=Decimal(str(importe_total)),
        estado=estado,
    )
    db.session.add(factura)
    return factura


class TestDashboardStats:
    def test_dashboard_defaults_to_current_month(self, client, auth_headers, db, tenant, facturador, receptor):
        today = date.today()
        current_month_day = today.replace(day=5)

        _create_factura(db, tenant.id, facturador.id, receptor.id, current_month_day, '1000.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor.id, current_month_day, '1200.00', estado='error')

        previous_month = date(today.year - 1, 12, 10) if today.month == 1 else date(today.year, today.month - 1, 10)
        _create_factura(db, tenant.id, facturador.id, receptor.id, previous_month, '9999.00', estado='autorizado')
        db.session.commit()

        response = client.get('/api/dashboard/stats', headers=auth_headers)
        assert response.status_code == 200

        payload = response.get_json()
        assert payload['facturas_mes'] == 2
        assert payload['autorizadas'] == 1
        assert payload['errores'] == 1
        assert payload['pendientes'] == 0
        assert payload['total_mes'] == 1000.0
        assert payload['filtros_aplicados']['historico'] is False
        assert len(payload['facturacion_12_meses']) == 12

    def test_dashboard_month_filter_applies_to_all_stats(self, client, auth_headers, db, tenant, facturador, receptor):
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 10), '1000.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 11), '200.00', estado='error')
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 12), '150.00', estado='pendiente')
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 13), '100.00', estado='borrador')

        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 2, 10), '9999.00', estado='pendiente')
        db.session.commit()

        response = client.get('/api/dashboard/stats?month=2026-01', headers=auth_headers)
        assert response.status_code == 200

        payload = response.get_json()
        assert payload['facturas_mes'] == 4
        assert payload['autorizadas'] == 1
        assert payload['errores'] == 1
        assert payload['pendientes'] == 2
        assert payload['total_mes'] == 1000.0
        assert payload['filtros_aplicados']['month'] == '2026-01'

    def test_dashboard_historico_includes_all_months(self, client, auth_headers, db, tenant, facturador, receptor):
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 10), '1000.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 2, 10), '1500.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 2, 12), '200.00', estado='pendiente')
        db.session.commit()

        response = client.get('/api/dashboard/stats?historico=true', headers=auth_headers)
        assert response.status_code == 200

        payload = response.get_json()
        assert payload['facturas_mes'] == 3
        assert payload['autorizadas'] == 2
        assert payload['pendientes'] == 1
        assert payload['total_mes'] == 2500.0
        assert payload['filtros_aplicados']['historico'] is True
        assert payload['ticket_promedio']['variacion_pct'] is None

    def test_dashboard_top_clientes_and_ticket_promedio(self, client, auth_headers, db, tenant, facturador):
        receptor_a = Receptor(
            tenant_id=tenant.id,
            doc_tipo=80,
            doc_nro='30111222333',
            razon_social='Cliente A',
            activo=True,
        )
        receptor_b = Receptor(
            tenant_id=tenant.id,
            doc_tipo=80,
            doc_nro='30222444555',
            razon_social='Cliente B',
            activo=True,
        )
        db.session.add_all([receptor_a, receptor_b])
        db.session.commit()

        _create_factura(db, tenant.id, facturador.id, receptor_a.id, date(2026, 1, 10), '1200.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor_a.id, date(2026, 1, 12), '800.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor_b.id, date(2026, 1, 15), '500.00', estado='autorizado')

        _create_factura(db, tenant.id, facturador.id, receptor_a.id, date(2025, 12, 10), '500.00', estado='autorizado')
        _create_factura(db, tenant.id, facturador.id, receptor_b.id, date(2025, 12, 11), '500.00', estado='autorizado')
        db.session.commit()

        response = client.get('/api/dashboard/stats?month=2026-01', headers=auth_headers)
        assert response.status_code == 200

        payload = response.get_json()

        assert payload['ticket_promedio']['valor'] == 833.3333333333334
        assert payload['ticket_promedio']['valor_periodo_anterior'] == 500.0
        assert payload['ticket_promedio']['variacion_pct'] == 66.67

        top_clientes = payload['top_clientes']
        assert len(top_clientes) == 2
        assert top_clientes[0]['razon_social'] == 'Cliente A'
        assert top_clientes[0]['total'] == 2000.0
        assert top_clientes[0]['porcentaje'] == 80.0

    def test_dashboard_is_tenant_isolated(self, client, auth_headers, db, tenant, facturador, receptor):
        other_tenant = Tenant(nombre='Otro tenant', slug='otro-tenant', activo=True)
        db.session.add(other_tenant)
        db.session.flush()

        other_facturador = Facturador(
            tenant_id=other_tenant.id,
            cuit='20999888776',
            razon_social='Otro Facturador',
            punto_venta=1,
            condicion_iva='IVA Responsable Inscripto',
            ambiente='testing',
            activo=True,
        )
        other_receptor = Receptor(
            tenant_id=other_tenant.id,
            doc_tipo=80,
            doc_nro='30999000111',
            razon_social='Otro Cliente',
            activo=True,
        )
        db.session.add_all([other_facturador, other_receptor])
        db.session.flush()

        _create_factura(db, tenant.id, facturador.id, receptor.id, date(2026, 1, 10), '1000.00', estado='autorizado')
        _create_factura(db, other_tenant.id, other_facturador.id, other_receptor.id, date(2026, 1, 11), '9000.00', estado='autorizado')
        db.session.commit()

        response = client.get('/api/dashboard/stats?month=2026-01', headers=auth_headers)
        assert response.status_code == 200

        payload = response.get_json()
        assert payload['facturas_mes'] == 1
        assert payload['total_mes'] == 1000.0
