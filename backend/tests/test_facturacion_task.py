from datetime import date
from decimal import Decimal

from app.models import Factura
from app.tasks.facturacion import procesar_factura


class _FakeClient:
    def fe_comp_ultimo_autorizado(self, punto_venta, tipo_cbte):
        return 100


class _FakeWSFE:
    captured_request = None

    def __init__(self, _client):
        pass

    def autorizar(self, request_data):
        _FakeWSFE.captured_request = request_data
        return {
            'cae': '12345678901234',
            'cae_vencimiento': '2026-12-31',
        }


class TestFacturacionTask:
    def test_procesar_factura_tipo_c_no_envia_iva(self, db, facturador, receptor, monkeypatch):
        factura = Factura(
            tenant_id=facturador.tenant_id,
            facturador_id=facturador.id,
            receptor_id=receptor.id,
            tipo_comprobante=11,
            concepto=1,
            punto_venta=facturador.punto_venta,
            fecha_emision=date(2026, 1, 15),
            fecha_desde=date(2026, 1, 15),
            fecha_hasta=date(2026, 1, 15),
            fecha_vto_pago=date(2026, 1, 15),
            importe_neto=Decimal('10000.00'),
            importe_iva=Decimal('2100.00'),
            importe_total=Decimal('12100.00'),
            moneda='PES',
            cotizacion=Decimal('1'),
            estado='pendiente',
        )
        db.session.add(factura)
        db.session.commit()

        monkeypatch.setattr('arca_integration.services.WSFEService', _FakeWSFE)

        result = procesar_factura(_FakeClient(), factura, facturador)
        assert result.get('success') is True

        req = _FakeWSFE.captured_request['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
        assert req['ImpNeto'] == 10000.0
        assert req['ImpIVA'] == 0.0
        assert req['ImpTotal'] == 10000.0
        assert 'Iva' not in req
