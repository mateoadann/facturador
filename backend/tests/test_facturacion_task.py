from datetime import date
from decimal import Decimal

from app.models import Factura
from app.tasks.facturacion import (
    procesar_factura,
    _is_retryable_sequence_error,
    _sync_factura_date_with_last_authorized,
)


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


class _FakeClientDateSync:
    def __init__(self, ultimo=123, fecha_cbte='20260220'):
        self.ultimo = ultimo
        self.fecha_cbte = fecha_cbte

    def fe_comp_ultimo_autorizado(self, punto_venta, tipo_cbte):
        return self.ultimo

    def fe_comp_consultar(self, tipo_cbte, punto_venta, numero):
        return {
            'encontrado': True,
            'fecha_cbte': self.fecha_cbte,
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

    def test_retryable_sequence_error_detects_10016(self):
        assert _is_retryable_sequence_error({
            'success': False,
            'error_code': '10016',
            'error_message': 'El numero o fecha del comprobante no se corresponde',
        }) is True

    def test_retryable_sequence_error_detects_message_fragment(self):
        assert _is_retryable_sequence_error({
            'success': False,
            'error_message': 'Consultar metodo FECompUltimoAutorizado para el proximo a autorizar',
        }) is True

    def test_retryable_sequence_error_ignores_success(self):
        assert _is_retryable_sequence_error({'success': True}) is False

    def test_sync_factura_date_with_last_authorized_adjusts_older_date(self, db, facturador, receptor):
        factura = Factura(
            tenant_id=facturador.tenant_id,
            facturador_id=facturador.id,
            receptor_id=receptor.id,
            tipo_comprobante=1,
            concepto=1,
            punto_venta=facturador.punto_venta,
            fecha_emision=date(2026, 1, 15),
            importe_neto=Decimal('100.00'),
            importe_iva=Decimal('21.00'),
            importe_total=Decimal('121.00'),
            moneda='PES',
            cotizacion=Decimal('1'),
            estado='pendiente',
        )

        changed = _sync_factura_date_with_last_authorized(
            _FakeClientDateSync(ultimo=555, fecha_cbte='20260220'),
            factura,
        )

        assert changed is True
        assert factura.fecha_emision == date(2026, 2, 20)

    def test_sync_factura_date_with_last_authorized_keeps_newer_date(self, db, facturador, receptor):
        factura = Factura(
            tenant_id=facturador.tenant_id,
            facturador_id=facturador.id,
            receptor_id=receptor.id,
            tipo_comprobante=1,
            concepto=1,
            punto_venta=facturador.punto_venta,
            fecha_emision=date(2026, 3, 1),
            importe_neto=Decimal('100.00'),
            importe_iva=Decimal('21.00'),
            importe_total=Decimal('121.00'),
            moneda='PES',
            cotizacion=Decimal('1'),
            estado='pendiente',
        )

        changed = _sync_factura_date_with_last_authorized(
            _FakeClientDateSync(ultimo=555, fecha_cbte='20260220'),
            factura,
        )

        assert changed is False
        assert factura.fecha_emision == date(2026, 3, 1)
