import pytest
from decimal import Decimal
from datetime import date
from app.services.csv_parser import parse_csv, clean_cuit, parse_date, parse_decimal


class TestParseCSV:
    def test_parse_valid_csv(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30-11111111-1,1,1,2026-01-15,1210.00,1000.00,210.00,Servicio web,1,1000.00
30-22222222-2,1,1,2026-01-16,2420.00,2000.00,420.00,Consultoría,2,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 2
        assert len(errors) == 0
        assert facturas[0]['receptor_cuit'] == '30111111111'
        assert facturas[0]['tipo_comprobante'] == 1
        assert facturas[0]['concepto'] == 1
        assert facturas[0]['importe_total'] == Decimal('1210.00')
        assert facturas[0]['importe_neto'] == Decimal('1000.00')
        assert facturas[0]['importe_iva'] == Decimal('210.00')
        assert facturas[0]['_validation_error'] is None
        assert len(facturas[0]['items']) == 1

    def test_parse_csv_missing_columns(self):
        csv_content = """receptor_cuit,tipo_comprobante
30111111111,1"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Columnas requeridas faltantes' in errors[0]
        # Verify that new required columns like item_descripcion are detected as missing
        assert 'item_descripcion' in errors[0]
        assert 'importe_iva' in errors[0]

    def test_parse_csv_with_optional_columns(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,fecha_desde,fecha_hasta,fecha_vto_pago
30111111111,1,2,2026-01-15,1210.00,1000.00,210.00,Servicio web,1,1000.00,2026-01-01,2026-01-31,2026-02-10"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['importe_iva'] == Decimal('210.00')
        assert facturas[0]['fecha_desde'] == date(2026, 1, 1)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 31)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 2, 10)
        assert facturas[0]['_validation_error'] is None

    def test_parse_csv_moneda_cotizacion_silently_ignored(self):
        """moneda and cotizacion columns are silently ignored if present."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,moneda,cotizacion
30111111111,1,1,2026-01-15,1210.00,1000.00,210.00,Servicio web,1,1000.00,PES,1"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        # moneda/cotizacion are NOT in the parsed factura
        assert 'moneda' not in facturas[0]
        assert 'cotizacion' not in facturas[0]
        assert facturas[0]['_validation_error'] is None

    def test_parse_csv_with_items(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,1210.00,1000.00,210.00,Servicio web,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert 'items' in facturas[0]
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio web'
        assert facturas[0]['items'][0]['cantidad'] == Decimal('1')
        assert facturas[0]['items_sin_iva'] == False
        assert facturas[0]['importe_neto'] == Decimal('1000.00')
        assert facturas[0]['importe_iva'] == Decimal('210.00')
        assert facturas[0]['importe_total'] == Decimal('1210.00')
        assert facturas[0]['_declared_importe_total'] == Decimal('1210.00')
        assert facturas[0]['_declared_importe_neto'] == Decimal('1000.00')
        assert facturas[0]['_declared_importe_iva'] == Decimal('210.00')
        assert facturas[0]['_validation_error'] is None

    def test_parse_csv_groups_multiple_rows_into_single_factura(self):
        """Items with different importes are grouped; importe_iva from CSV is used."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,fecha_desde,fecha_hasta,fecha_vto_pago
30111111111,1,2,2026-01-15,181500.00,150000.00,31500.00,Servicio mensual,1,100000.00,2026-01-01,2026-01-31,2026-01-20
30111111111,1,2,2026-01-15,181500.00,150000.00,31500.00,Soporte técnico,1,50000.00,2026-01-01,2026-01-31,2026-01-20"""

        facturas, errors = parse_csv(csv_content)

        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['items_sin_iva'] == False
        assert facturas[0]['importe_neto'] == Decimal('150000.00')
        assert facturas[0]['importe_iva'] == Decimal('31500.00')
        assert facturas[0]['importe_total'] == Decimal('181500.00')
        assert len(facturas[0]['items']) == 2
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio mensual'
        assert facturas[0]['items'][1]['descripcion'] == 'Soporte técnico'
        assert facturas[0]['_validation_error'] is None

    def test_parse_csv_invalid_row(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,abc,1,2026-01-15,1210.00,1000.00,210.00,Servicio,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Fila 2' in errors[0]

    def test_parse_csv_with_nota_credito(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,cbte_asoc_tipo,cbte_asoc_pto_vta,cbte_asoc_nro
30111111111,3,1,2026-01-20,1210.00,1000.00,210.00,Devolución servicio,1,1000.00,1,1,100"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0]['cbte_asoc_tipo'] == 1
        assert facturas[0]['cbte_asoc_pto_vta'] == 1
        assert facturas[0]['cbte_asoc_nro'] == 100
        assert facturas[0]['_validation_error'] is None

    def test_parse_csv_concepto_2_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-20,1210.00,1000.00,210.00,Servicio web,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_3_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,3,2026-01-20,1210.00,1000.00,210.00,Producto + servicio,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_2_with_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,fecha_desde,fecha_hasta,fecha_vto_pago
30111111111,1,2,2026-01-20,1210.00,1000.00,210.00,Servicio web,1,1000.00,2026-01-01,2026-01-31,2026-02-10"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 1)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 31)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 2, 10)

    def test_parse_csv_concepto_1_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-20,1210.00,1000.00,210.00,Producto,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_1_defaults_only_missing_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,fecha_desde
30111111111,1,1,2026-01-20,1210.00,1000.00,210.00,Producto,1,1000.00,2026-01-15"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 15)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_2_defaults_only_missing_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario,fecha_desde
30111111111,1,2,2026-01-20,1210.00,1000.00,210.00,Servicio,1,1000.00,2026-01-10"""

        facturas, errors = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 10)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_empty_csv(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 0

    def test_parse_csv_cross_validation_mismatch(self):
        """Declared totals don't match computed from items → _validation_error is set."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,999.00,800.00,100.00,Widget,1,100.00"""
        # item: 100 * 1 = 100 neto computed
        # declared neto = 800 → mismatch (800 vs 100)
        # declared total = 999 → mismatch (computed = 100 + 100 = 200 vs 999)

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['_validation_error'] is not None
        assert 'importe_total' in facturas[0]['_validation_error']
        assert 'importe_neto' in facturas[0]['_validation_error']

    def test_parse_csv_cross_validation_passes_within_tolerance(self):
        """Declared totals differ by <= 0.02 from computed → _validation_error is None."""
        # item: 1000 * 1 = 1000 neto, iva = 210, total = 1210
        # declared values off by 0.01 each (within 0.02 tolerance)
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,1210.01,1000.01,210.01,Servicio,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['_validation_error'] is None
        # Computed values come from items, not declared
        assert facturas[0]['importe_neto'] == Decimal('1000.00')
        assert facturas[0]['importe_iva'] == Decimal('210.01')
        assert facturas[0]['importe_total'] == Decimal('1210.01')
        # Declared values are preserved
        assert facturas[0]['_declared_importe_total'] == Decimal('1210.01')
        assert facturas[0]['_declared_importe_neto'] == Decimal('1000.01')
        assert facturas[0]['_declared_importe_iva'] == Decimal('210.01')

    def test_parse_csv_missing_item_descripcion_required_column(self):
        """Missing item_descripcion in header triggers the required columns error."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,1210.00,1000.00,210.00,1,1000.00"""

        facturas, errors = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Columnas requeridas faltantes' in errors[0]
        assert 'item_descripcion' in errors[0]


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
