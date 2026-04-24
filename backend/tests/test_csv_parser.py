import pytest
from decimal import Decimal
from datetime import date
from app.services.csv_parser import (
    parse_csv, clean_cuit, parse_date, parse_decimal,
    detect_delimiter, detect_number_format, normalize_headers,
    resolve_tipo_comprobante, parse_int_optional,
)


class TestParseCSV:
    def test_parse_valid_csv(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30-11111111-1,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00
30-22222222-2,1,1,2026-01-16,24200.00,20000.00,4200.00,Servicio B,1,20000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 2
        assert len(errors) == 0
        assert facturas[0]['receptor_cuit'] == '30111111111'
        assert facturas[0]['tipo_comprobante'] == 1
        assert facturas[0]['concepto'] == 1
        assert facturas[0]['importe_total'] == Decimal('12100.00')
        assert facturas[0]['importe_neto'] == Decimal('10000.00')

    def test_parse_csv_missing_columns(self):
        csv_content = """receptor_cuit
30111111111"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Columnas requeridas faltantes' in errors[0]

    def test_parse_csv_with_optional_columns(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,moneda,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-15,12100.00,10000.00,2100.00,PES,Servicio mensual,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['importe_iva'] == Decimal('2100.00')
        assert 'moneda' not in facturas[0]

    def test_parse_csv_with_items(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert 'items' in facturas[0]
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio web'
        assert facturas[0]['items'][0]['cantidad'] == Decimal('1')
        assert facturas[0]['importe_neto'] == Decimal('10000.00')
        assert facturas[0]['importe_iva'] == Decimal('2100.00')
        assert facturas[0]['importe_total'] == Decimal('12100.00')

    def test_parse_csv_factura_a_without_iva_returns_validation_error(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,10000.00,10000.00,0,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0]['_validation_error'] is not None
        assert 'Factura A' in facturas[0]['_validation_error']
        assert 'importe_iva' in facturas[0]['_validation_error']

    def test_parse_csv_factura_b_without_iva_returns_validation_error(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,6,1,2026-01-15,10000.00,10000.00,0,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0]['_validation_error'] is not None
        assert 'Factura B' in facturas[0]['_validation_error']

    def test_parse_csv_factura_c_without_iva_succeeds(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,11,1,2026-01-15,10000.00,10000.00,0,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0].get('_validation_error') is None
        assert facturas[0]['importe_iva'] == Decimal('0')
        assert facturas[0]['importe_total'] == Decimal('10000.00')

    def test_parse_csv_groups_multiple_rows_into_single_factura(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,fecha_desde,fecha_hasta,fecha_vto_pago,importe_iva,moneda,cotizacion,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-15,121000.00,100000.00,2026-01-01,2026-01-31,2026-01-20,31500.00,PES,1,Servicio mensual,1,100000.00
30111111111,1,2,2026-01-15,60500.00,50000.00,2026-01-01,2026-01-31,2026-01-20,31500.00,PES,1,Soporte técnico,1,50000.00"""

        facturas, errors, warnings = parse_csv(csv_content)

        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['importe_neto'] == Decimal('150000.00')
        assert facturas[0]['importe_iva'] == Decimal('31500.00')
        assert facturas[0]['importe_total'] == Decimal('181500.00')
        assert len(facturas[0]['items']) == 2
        assert facturas[0]['items'][0]['descripcion'] == 'Servicio mensual'
        assert facturas[0]['items'][1]['descripcion'] == 'Soporte técnico'

    def test_parse_csv_groups_repeated_totals_no_iva_factura_a_returns_error(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,300.00,300.00,0,Servicio mensual,1,100.00
30111111111,1,1,2026-01-15,300.00,300.00,0,Sueldos,1,100.00
30111111111,1,1,2026-01-15,300.00,300.00,0,Honorarios,1,100.00"""

        facturas, errors, warnings = parse_csv(csv_content)

        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['_validation_error'] is not None
        assert 'Factura A' in facturas[0]['_validation_error']
        assert facturas[0]['importe_neto'] == Decimal('300.00')
        assert facturas[0]['importe_iva'] == Decimal('0')
        assert facturas[0]['importe_total'] == Decimal('300.00')
        assert len(facturas[0]['items']) == 3

    def test_parse_csv_invalid_row(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,abc,1,2026-01-15,12100.00,10000.00,2100.00,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 0
        assert len(errors) == 1
        assert 'Fila 2' in errors[0]

    def test_parse_csv_with_nota_credito_legacy_fields(self):
        """NC with explicit cbte_asoc fields (legacy format)."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,cbte_asoc_tipo,cbte_asoc_pto_vta,cbte_asoc_nro,item_descripcion,item_cantidad,item_precio_unitario
30111111111,3,1,2026-01-20,5000.00,4132.23,867.77,1,1,100,Nota credito,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert facturas[0]['cbte_asoc_tipo'] == 1
        assert facturas[0].get('cbte_asoc_pto_vta') == 1
        assert facturas[0]['cbte_asoc_nro'] == 100

    def test_parse_csv_concepto_2_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-20,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_3_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,3,2026-01-20,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_2_with_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,fecha_desde,fecha_hasta,fecha_vto_pago,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-20,2026-01-01,2026-01-31,2026-02-10,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 1)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 31)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 2, 10)

    def test_parse_csv_concepto_1_defaults_service_dates_to_emision(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-20,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 20)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_1_defaults_only_missing_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,fecha_desde,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-20,2026-01-15,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 15)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_csv_concepto_2_defaults_only_missing_service_dates(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,fecha_desde,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-20,2026-01-10,5000.00,4132.23,867.77,Servicio,1,4132.23"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['fecha_desde'] == date(2026, 1, 10)
        assert facturas[0]['fecha_hasta'] == date(2026, 1, 20)
        assert facturas[0]['fecha_vto_pago'] == date(2026, 1, 20)

    def test_parse_empty_csv(self):
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario"""

        facturas, errors, warnings = parse_csv(csv_content)
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

    def test_parse_decimal_argentine_format(self):
        result = parse_decimal('6.277.822,35', 'test', number_format='ar')
        assert result == Decimal('6277822.35')

    def test_parse_decimal_argentine_simple(self):
        result = parse_decimal('1.234,56', 'test', number_format='ar')
        assert result == Decimal('1234.56')

    def test_parse_decimal_argentine_no_thousands(self):
        result = parse_decimal('822,35', 'test', number_format='ar')
        assert result == Decimal('822.35')

    def test_parse_decimal_anglo_with_thousands_comma(self):
        result = parse_decimal('1,234.56', 'test', number_format='en')
        assert result == Decimal('1234.56')

    def test_parse_decimal_anglo_plain(self):
        result = parse_decimal('6277822.35', 'test', number_format='en')
        assert result == Decimal('6277822.35')


class TestDetectDelimiter:
    def test_detect_comma_delimiter(self):
        content = "receptor_cuit,tipo_comprobante,concepto\n30111,1,2"
        assert detect_delimiter(content) == ','

    def test_detect_semicolon_delimiter(self):
        content = "CUIT;TIPO_COMP;DETALLE FACTURA\n30111;A;Balance"
        assert detect_delimiter(content) == ';'

    def test_detect_semicolon_with_comma_in_values(self):
        content = 'CUIT;NETO_UNI;TOTAL\n30111;"1.234,56";"2.345,67"'
        assert detect_delimiter(content) == ';'

    def test_detect_comma_with_no_semicolons(self):
        content = "a,b,c,d\n1,2,3,4"
        assert detect_delimiter(content) == ','


class TestDetectNumberFormat:
    def test_semicolon_implies_argentine(self):
        assert detect_number_format("CUIT;NETO", ';') == 'ar'

    def test_comma_delimiter_implies_anglo(self):
        assert detect_number_format("CUIT,NETO\n30111,1234.56", ',') == 'en'

    def test_comma_delimiter_with_argentine_numbers_detected(self):
        content = "CUIT,NETO\n30111,6.277.822"
        assert detect_number_format(content, ',') == 'ar'


class TestNormalizeHeaders:
    def test_maps_excel_headers(self):
        headers = ['CUIT', 'TIPO_COMP', 'DETALLE FACTURA', 'NETO_UNI', 'CANT']
        result = normalize_headers(headers)
        assert result == ['receptor_cuit', 'tipo_comprobante', 'item_descripcion', 'item_precio_unitario', 'item_cantidad']

    def test_passes_through_internal_headers(self):
        headers = ['receptor_cuit', 'tipo_comprobante', 'concepto']
        result = normalize_headers(headers)
        assert result == ['receptor_cuit', 'tipo_comprobante', 'concepto']

    def test_strips_bom(self):
        headers = ['\ufeffCUIT', 'TIPO_COMP']
        result = normalize_headers(headers)
        assert result == ['receptor_cuit', 'tipo_comprobante']

    def test_handles_none_header(self):
        headers = [None, 'CUIT']
        result = normalize_headers(headers)
        assert result[0] == '_unknown_0'
        assert result[1] == 'receptor_cuit'

    def test_case_insensitive(self):
        headers = ['cuit', 'Tipo_Comp', 'Detalle Factura']
        result = normalize_headers(headers)
        assert result == ['receptor_cuit', 'tipo_comprobante', 'item_descripcion']


class TestResolveTipoComprobante:
    def test_letter_codes(self):
        assert resolve_tipo_comprobante('A') == 1
        assert resolve_tipo_comprobante('B') == 6
        assert resolve_tipo_comprobante('C') == 11

    def test_nota_credito_codes(self):
        assert resolve_tipo_comprobante('NCA') == 3
        assert resolve_tipo_comprobante('NCB') == 8
        assert resolve_tipo_comprobante('NCC') == 13

    def test_nota_debito_codes(self):
        assert resolve_tipo_comprobante('NDA') == 2
        assert resolve_tipo_comprobante('NDB') == 7
        assert resolve_tipo_comprobante('NDC') == 12

    def test_case_insensitive(self):
        assert resolve_tipo_comprobante('nca') == 3
        assert resolve_tipo_comprobante('Ndb') == 7
        assert resolve_tipo_comprobante('a') == 1

    def test_numeric_codes(self):
        assert resolve_tipo_comprobante('1') == 1
        assert resolve_tipo_comprobante('6') == 6
        assert resolve_tipo_comprobante('11') == 11
        assert resolve_tipo_comprobante('3') == 3

    def test_invalid_code(self):
        with pytest.raises(ValueError):
            resolve_tipo_comprobante('X')

    def test_empty(self):
        with pytest.raises(ValueError):
            resolve_tipo_comprobante('')

    def test_invalid_numeric(self):
        with pytest.raises(ValueError):
            resolve_tipo_comprobante('999')


class TestParseIntOptional:
    def test_returns_none_for_empty(self):
        assert parse_int_optional('', 'test') is None
        assert parse_int_optional(None, 'test') is None
        assert parse_int_optional('  ', 'test') is None

    def test_parses_valid_int(self):
        assert parse_int_optional('42', 'test') == 42

    def test_raises_for_invalid(self):
        with pytest.raises(ValueError):
            parse_int_optional('abc', 'test')


class TestExcelFormatCSV:
    """Integration tests for Excel-exported CSV format."""

    def test_excel_format_semicolon_argentine(self):
        """Full Excel-format CSV with semicolons and Argentine numbers."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP\n'
        csv_content += '30715441205;A;Balance 2025;6.277.822,35;1;6.277.822,35;1.318.342,69;7.596.165,04;17/04/2026'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert len(facturas) == 1
        f = facturas[0]
        assert f['receptor_cuit'] == '30715441205'
        assert f['tipo_comprobante'] == 1
        assert f['concepto'] == 2
        assert f['items'][0]['descripcion'] == 'Balance 2025'
        assert f['items'][0]['precio_unitario'] == Decimal('6277822.35')
        assert f['importe_iva'] == Decimal('1318342.69')

    def test_excel_format_nota_credito(self):
        """Excel format with NCA tipo and NRO_FAC."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP;NRO_FAC\n'
        csv_content += '30715441205;NCA;Ajuste;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026;500'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert len(facturas) == 1
        f = facturas[0]
        assert f['tipo_comprobante'] == 3  # NCA = 3
        assert f['cbte_asoc_tipo'] == 1    # NCA → FA A (1)
        assert f['cbte_asoc_nro'] == 500

    def test_excel_format_with_email_override(self):
        """Excel format with MAIL column overriding receptor email."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP;MAIL;ASUNTO_MAIL;MENSAJE_MAIL\n'
        csv_content += '30715441205;A;Balance;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026;admin@test.com;Factura Balance;Buenos dias!'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['email_override'] == 'admin@test.com'
        assert facturas[0]['email_asunto'] == 'Factura Balance'
        assert facturas[0]['email_mensaje'] == 'Buenos dias!'

    def test_excel_format_multiple_emails(self):
        """MAIL column with multiple comma-separated emails."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP;MAIL\n'
        csv_content += '30715441205;A;Balance;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026;"admin@test.com,cfo@test.com"'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert facturas[0]['email_override'] == 'admin@test.com,cfo@test.com'

    def test_excel_format_concepto_from_default(self):
        """Concepto comes from facturador default when CSV has no concepto column."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP\n'
        csv_content += '30715441205;A;Servicio;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert facturas[0]['concepto'] == 2

    def test_excel_format_no_concepto_no_default_errors(self):
        """No concepto column and no default → error."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP\n'
        csv_content += '30715441205;A;Servicio;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=None)
        assert len(errors) == 1
        assert 'concepto' in errors[0]

    def test_excel_format_ignores_unknown_columns(self):
        """Unknown columns (PERIODO, CLIENTE, etc.) are silently ignored."""
        csv_content = 'PERIODO;CUIT;TIPO_COMP;CLIENTE;DETALLE FACTURA;extra reporte jose;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP;NOMBRE_LOTE\n'
        csv_content += '2026-04;30715441205;A;Humber SA;Balance;balance;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026;ABRIL2026'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert facturas[0]['receptor_cuit'] == '30715441205'

    def test_excel_format_empty_rows_skipped(self):
        """Rows with empty CUIT are skipped."""
        csv_content = 'CUIT;TIPO_COMP;DETALLE FACTURA;NETO_UNI;CANT;NETO_TOTAL;IVA;TOTAL;EMISION_COMP\n'
        csv_content += '30715441205;A;Balance;1.000,00;1;1.000,00;210,00;1.210,00;17/04/2026\n'
        csv_content += ';;;;;;;;'

        facturas, errors, warnings = parse_csv(csv_content, concepto_default=2)
        assert len(errors) == 0
        assert len(facturas) == 1

    def test_cross_validation_is_warning_not_error(self):
        """Cross-validation mismatches are warnings, not errors."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,1,2026-01-15,99999.00,10000.00,2100.00,Servicio web,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(warnings) > 0
        assert 'importe_total' in warnings[0]
        # Should be a warning, not blocking
        assert facturas[0].get('_validation_error') is None or 'importe_total' not in (facturas[0].get('_validation_error') or '')

    def test_bom_stripped(self):
        """BOM at start of file is handled."""
        csv_content = '\ufeffreceptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario\n'
        csv_content += '30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio,1,10000.00'

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1

    def test_backward_compat_internal_format(self):
        """Old internal CSV format still works unchanged."""
        csv_content = """receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario
30111111111,1,2,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['tipo_comprobante'] == 1
        assert facturas[0]['concepto'] == 2


class TestEmailCsvColumns:
    """Tests para columnas opcionales de email override en CSV."""

    HEADER = 'receptor_cuit,tipo_comprobante,concepto,fecha_emision,importe_total,importe_neto,importe_iva,item_descripcion,item_cantidad,item_precio_unitario'

    def test_csv_without_email_columns_backward_compatible(self):
        csv_content = f"""{self.HEADER}
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert 'emails_cc' not in facturas[0]
        assert 'email_asunto' not in facturas[0]
        assert 'email_mensaje' not in facturas[0]
        assert 'email_firma' not in facturas[0]

    def test_csv_with_valid_emails_cc(self):
        csv_content = f"""{self.HEADER},emails_cc
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,"admin@test.com,contador@test.com"
"""
        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['emails_cc'] == 'admin@test.com,contador@test.com'

    def test_csv_with_invalid_emails_cc_format(self):
        csv_content = f"""{self.HEADER},emails_cc
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,no-es-email"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 1
        assert 'emails_cc' in errors[0]
        assert 'formato inválido' in errors[0]

    def test_csv_with_more_than_10_emails_cc(self):
        emails = ','.join([f'user{i}@test.com' for i in range(11)])
        csv_content = f"""{self.HEADER},emails_cc
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,"{emails}"
"""
        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 1
        assert 'máximo' in errors[0]
        assert '10' in errors[0]

    def test_csv_with_partial_content_override_only_asunto(self):
        csv_content = f"""{self.HEADER},email_asunto
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,Factura Custom"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['email_asunto'] == 'Factura Custom'
        assert 'email_mensaje' not in facturas[0]
        assert 'email_firma' not in facturas[0]

    def test_csv_with_all_email_override_fields(self):
        csv_content = f"""{self.HEADER},emails_cc,email_asunto,email_mensaje,email_firma
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,"cc@test.com",Asunto Custom,Mensaje custom,Firma custom"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['emails_cc'] == 'cc@test.com'
        assert facturas[0]['email_asunto'] == 'Asunto Custom'
        assert facturas[0]['email_mensaje'] == 'Mensaje custom'
        assert facturas[0]['email_firma'] == 'Firma custom'

    def test_two_rows_different_emails_cc_group_correctly(self):
        csv_content = f"""{self.HEADER},emails_cc
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,5000.00,"cc1@test.com"
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio B,1,5000.00,"cc2@test.com"
"""
        facturas, errors, warnings = parse_csv(csv_content)
        assert len(errors) == 0
        assert len(facturas) == 1
        assert len(facturas[0]['items']) == 2
        assert facturas[0].get('emails_cc') == 'cc1@test.com'

    def test_csv_mensaje_firma_without_asunto_generates_warning(self):
        csv_content = f"""{self.HEADER},email_mensaje,email_firma
30111111111,1,1,2026-01-15,12100.00,10000.00,2100.00,Servicio A,1,10000.00,Mensaje custom,Firma custom"""

        facturas, errors, warnings = parse_csv(csv_content)
        assert len(facturas) == 1
        assert len(errors) == 0
        assert facturas[0]['_email_override_warning'] == 'email_mensaje y email_firma se ignoran sin email_asunto'
        assert 'email_mensaje' not in facturas[0]
        assert 'email_firma' not in facturas[0]

    def test_email_columns_in_group_key_exclude(self):
        from app.services.csv_parser import GROUP_KEY_EXCLUDE_COLUMNS
        assert 'emails_cc' in GROUP_KEY_EXCLUDE_COLUMNS
        assert 'email_asunto' in GROUP_KEY_EXCLUDE_COLUMNS
        assert 'email_mensaje' in GROUP_KEY_EXCLUDE_COLUMNS
        assert 'email_firma' in GROUP_KEY_EXCLUDE_COLUMNS
        assert 'email_override' in GROUP_KEY_EXCLUDE_COLUMNS
