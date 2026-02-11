import pytest
from decimal import Decimal
from datetime import date
from app.services.csv_parser import parse_csv, clean_cuit, parse_date, parse_decimal


class TestParseCSV:
    def test_parse_valid_csv(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
20-12345678-9,30-11111111-1,1,1,2026-01-15,12100.00,10000.00
20-12345678-9,30-22222222-2,1,1,2026-01-16,24200.00,20000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 2
        assert len(errors) == 0
        assert facturas[0]['facturador_cuit'] == '20123456789'
        assert facturas[0]['receptor_cuit'] == '30111111111'
        assert facturas[0]['tipo_comprobante'] == 1
        assert facturas[0]['concepto'] == 1
        assert facturas[0]['importe_total'] == Decimal('12100.00')
        assert facturas[0]['importe_neto'] == Decimal('10000.00')

    def test_parse_csv_missing_columns(self):
        csv_content = """facturador_cuit,receptor_cuit
20123456789,30111111111"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Columnas requeridas faltantes' in errors[0]

    def test_parse_csv_with_optional_columns(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,moneda
20123456789,30111111111,1,2,2026-01-15,12100.00,10000.00,2100.00,PES"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['importe_iva'] == Decimal('2100.00')
        assert facturas[0]['moneda'] == 'PES'

    def test_parse_csv_with_items(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,item_descripcion,item_cantidad,item_precio_unitario
20123456789,30111111111,1,1,2026-01-15,12100.00,10000.00,Servicio web,1,10000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert 'items' in facturas[0]
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio web'
        assert facturas[0]['items'][0]['cantidad'] == Decimal('1')
        # Importes recalculados desde items: neto=10000, IVA 21%=2100, total=12100
        assert facturas[0]['importe_neto'] == Decimal('10000.00')
        assert facturas[0]['importe_iva'] == Decimal('2100.00')
        assert facturas[0]['importe_total'] == Decimal('12100.00')

    def test_parse_csv_groups_multiple_rows_into_single_factura(self):
        """Items con distintos importes se agrupan y recalculan desde items."""
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,fecha_desde,fecha_hasta,fecha_vto_pago,importe_iva,moneda,cotizacion,item_descripcion,item_cantidad,item_precio_unitario,item_alicuota_iva_id
20123456789,30111111111,1,2,2026-01-15,121000.00,100000.00,2026-01-01,2026-01-31,2026-01-20,21.00,PES,1,Servicio mensual,1,100000.00,5
20123456789,30111111111,1,2,2026-01-15,60500.00,50000.00,2026-01-01,2026-01-31,2026-01-20,21.00,PES,1,Soporte técnico,1,50000.00,5"""

        facturas, errors = parse_csv(csv_content)

        assert len(errors) == 0
        assert len(facturas) == 1
        # Importes recalculados desde items (100000 + 50000 = 150000 neto)
        assert facturas[0]['importe_neto'] == Decimal('150000.00')
        assert facturas[0]['importe_iva'] == Decimal('31500.00')
        assert facturas[0]['importe_total'] == Decimal('181500.00')
        assert len(facturas[0]['items']) == 2
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio mensual'
        assert facturas[0]['items'][1]['descripcion'] == 'Soporte técnico'

    def test_parse_csv_groups_repeated_totals_recalculates_from_items(self):
        """Cuando importes son iguales en cada fila pero hay items, recalcula desde items."""
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,item_descripcion,item_cantidad,item_precio_unitario,item_alicuota_iva_id
20123456789,30111111111,1,1,2026-01-15,100.00,100.00,Servicio mensual,1,100.00,5
20123456789,30111111111,1,1,2026-01-15,100.00,100.00,Sueldos,1,100.00,5
20123456789,30111111111,1,1,2026-01-15,100.00,100.00,Honorarios,1,100.00,5"""

        facturas, errors = parse_csv(csv_content)

        assert len(errors) == 0
        assert len(facturas) == 1
        # 3 items x $100 = $300 neto, IVA 21% = $63, total = $363
        assert facturas[0]['importe_neto'] == Decimal('300.00')
        assert facturas[0]['importe_iva'] == Decimal('63.00')
        assert facturas[0]['importe_total'] == Decimal('363.00')
        assert len(facturas[0]['items']) == 3

    def test_parse_csv_invalid_row(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto
20123456789,30111111111,abc,1,2026-01-15,12100.00,10000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Fila 2' in errors[0]

    def test_parse_csv_with_nota_credito(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,cbte_asoc_tipo,cbte_asoc_pto_vta,cbte_asoc_nro
20123456789,30111111111,3,1,2026-01-20,5000.00,4132.23,1,1,100"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0]['cbte_asoc_tipo'] == 1
        assert facturas[0]['cbte_asoc_pto_vta'] == 1
        assert facturas[0]['cbte_asoc_nro'] == 100

    def test_parse_empty_csv(self):
        csv_content = """facturador_cuit,receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 0


class TestCleanCuit:
    def test_clean_cuit_with_dashes(self):
        assert clean_cuit('20-12345678-9') == '20123456789'

    def test_clean_cuit_with_spaces(self):
        assert clean_cuit(' 20 12345678 9 ') == '20123456789'

    def test_clean_cuit_already_clean(self):
        assert clean_cuit('20123456789') == '20123456789'


class TestParseDate:
    def test_parse_date_iso(self):
        result = parse_date('2026-01-15', 'test')
        assert result == date(2026, 1, 15)

    def test_parse_date_ddmmyyyy(self):
        result = parse_date('15/01/2026', 'test')
        assert result == date(2026, 1, 15)

    def test_parse_date_invalid(self):
        with pytest.raises(ValueError):
            parse_date('invalid', 'test')

    def test_parse_date_empty(self):
        with pytest.raises(ValueError):
            parse_date('', 'test')

    def test_parse_date_with_spaces(self):
        result = parse_date(' 2026-01-15 ', 'test')
        assert result == date(2026, 1, 15)


class TestParseDecimal:
    def test_parse_decimal_point(self):
        result = parse_decimal('12100.50', 'test')
        assert result == Decimal('12100.50')

    def test_parse_decimal_comma(self):
        result = parse_decimal('12100,50', 'test')
        assert result == Decimal('12100.50')

    def test_parse_decimal_integer(self):
        result = parse_decimal('10000', 'test')
        assert result == Decimal('10000')

    def test_parse_decimal_invalid(self):
        with pytest.raises(ValueError):
            parse_decimal('abc', 'test')

    def test_parse_decimal_empty(self):
        with pytest.raises(ValueError):
            parse_decimal('', 'test')
