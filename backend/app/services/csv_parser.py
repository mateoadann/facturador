import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple


REQUIRED_COLUMNS = [
    'receptor_cuit',
    'tipo_comprobante',
    'concepto',
    'fecha_emision',
    'importe_total',
    'importe_neto',
    'importe_iva',
    'item_descripcion',
    'item_cantidad',
    'item_precio_unitario',
]

GROUP_KEY_EXCLUDE_COLUMNS = {
    'items',
    'importe_total',
    'importe_neto',
    'importe_iva',
    '_declared_importe_total',
    '_declared_importe_neto',
    '_declared_importe_iva',
    '_validation_error',
    'emails_cc',
    'email_asunto',
    'email_mensaje',
    'email_firma',
}

OPTIONAL_COLUMNS = [
    'fecha_desde',
    'fecha_hasta',
    'fecha_vto_pago',
    'cbte_asoc_tipo',
    'cbte_asoc_pto_vta',
    'cbte_asoc_nro',
    'emails_cc',
    'email_asunto',
    'email_mensaje',
    'email_firma',
]

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
MAX_CC_EMAILS = 10


def parse_csv(file_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parsea el contenido CSV y retorna una lista de facturas y errores.

    Returns:
        Tuple[List[Dict], List[str]]: (facturas_parseadas, errores)
    """
    errors = []
    grouped_facturas = {}
    grouped_order = []

    try:
        reader = csv.DictReader(io.StringIO(file_content))
        columns = reader.fieldnames or []

        # Validar columnas requeridas
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in columns]
        if missing_columns:
            return [], [f"Columnas requeridas faltantes: {', '.join(missing_columns)}"]

        for row_num, row in enumerate(reader, start=2):
            try:
                factura = parse_factura_row(row, row_num)
                if factura:
                    key = build_factura_group_key(factura)
                    if key not in grouped_facturas:
                        grouped_facturas[key] = {
                            'factura': {k: v for k, v in factura.items() if k != 'items'},
                            'importe_total_rows': [],
                            'importe_neto_rows': [],
                            'importe_iva_rows': [],
                            'items': [],
                        }
                        grouped_order.append(key)

                    grouped = grouped_facturas[key]
                    grouped['importe_total_rows'].append(factura.get('importe_total'))
                    grouped['importe_neto_rows'].append(factura.get('importe_neto'))
                    grouped['importe_iva_rows'].append(factura.get('importe_iva'))

                    grouped['items'].extend(factura['items'])
            except ValueError as e:
                errors.append(f"Fila {row_num}: {str(e)}")

    except csv.Error as e:
        return [], [f"Error al parsear CSV: {str(e)}"]

    facturas = []
    for key in grouped_order:
        grouped = grouped_facturas[key]
        factura = grouped['factura']

        factura['items'] = grouped['items']
        # Items siempre presentes: recalcular importes desde los items
        factura = _recalculate_from_items(factura, grouped)

        # Sum declared values from ALL rows before cross-validation
        factura['_declared_importe_total'] = sum(grouped['importe_total_rows'])
        factura['_declared_importe_neto'] = sum(grouped['importe_neto_rows'])
        factura['_declared_importe_iva'] = sum(grouped['importe_iva_rows'])

        # Cross-validation: comparar declarados vs calculados (T2)
        cross_error = _cross_validate_importes(factura)
        recalc_error = factura.get('_validation_error')

        # Merge validation errors from recalculation and cross-validation
        all_errors = [e for e in (recalc_error, cross_error) if e]
        factura['_validation_error'] = '; '.join(all_errors) if all_errors else None

        facturas.append(factura)

    return facturas, errors


def _recalculate_from_items(factura: Dict[str, Any], grouped: Dict) -> Dict[str, Any]:
    """Recalcula importes desde los items.

    Si viene importe_iva del CSV, se distribuye proporcionalmente por item.
    Si NO viene importe_iva y el tipo es A (1,2,3) o B (6,7,8), es un error de validación.
    Si NO viene importe_iva y el tipo es C (11,12,13), se acepta con IVA=0.
    """
    items = factura['items']
    tipo = factura.get('tipo_comprobante')

    # Tipos que REQUIEREN IVA
    TIPOS_A = {1, 2, 3}
    TIPOS_B = {6, 7, 8}

    # Calcular subtotal de cada item (precio * cantidad)
    for item in items:
        item['subtotal'] = (item['cantidad'] * item['precio_unitario']).quantize(Decimal('0.01'))

    importe_neto_total = sum(item['subtotal'] for item in items).quantize(Decimal('0.01'))

    # Verificar si viene importe_iva del CSV
    importe_iva_csv = resolve_grouped_amount(grouped.get('importe_iva_rows', []))

    if importe_iva_csv is not None and importe_iva_csv > 0:
        for item in items:
            proporcion = item['subtotal'] / importe_neto_total if importe_neto_total > 0 else Decimal('0')
            item['importe_iva'] = (importe_iva_csv * proporcion).quantize(Decimal('0.02'))
            item['importe_neto'] = item['subtotal']

        factura['importe_iva'] = importe_iva_csv.quantize(Decimal('0.01'))
    else:
        # No viene IVA — validar según tipo de comprobante
        if tipo in TIPOS_A or tipo in TIPOS_B:
            letra = 'A' if tipo in TIPOS_A else 'B'
            factura['_validation_error'] = (
                f'Factura {letra} (tipo {tipo}) requiere importe_iva mayor a 0. '
                f'Las facturas tipo {letra} deben incluir IVA.'
            )

        for item in items:
            item['importe_iva'] = Decimal('0')
            item['importe_neto'] = item['subtotal']
        factura['importe_iva'] = Decimal('0')

    factura['importe_neto'] = importe_neto_total
    factura['importe_total'] = (importe_neto_total + factura['importe_iva']).quantize(Decimal('0.01'))

    return factura


def _cross_validate_importes(factura: Dict[str, Any]) -> str | None:
    """Validates that declared importes match computed importes.

    Returns error message string if mismatch, None if OK.
    Tolerance: Decimal('0.02') to absorb rounding artifacts.
    """
    tolerance = Decimal('0.02')

    declared_total = factura.get('_declared_importe_total')
    declared_neto = factura.get('_declared_importe_neto')
    declared_iva = factura.get('_declared_importe_iva')

    computed_total = factura['importe_total']
    computed_neto = factura['importe_neto']
    computed_iva = factura['importe_iva']

    errors = []

    if declared_total is not None and abs(computed_total - declared_total) > tolerance:
        errors.append(f"importe_total declarado ({declared_total}) != calculado ({computed_total})")

    if declared_neto is not None and abs(computed_neto - declared_neto) > tolerance:
        errors.append(f"importe_neto declarado ({declared_neto}) != calculado ({computed_neto})")

    if declared_iva is not None and abs(computed_iva - declared_iva) > tolerance:
        errors.append(f"importe_iva declarado ({declared_iva}) != calculado ({computed_iva})")

    return "; ".join(errors) if errors else None


def build_factura_group_key(factura: Dict[str, Any]) -> tuple:
    key_data = {
        key: value
        for key, value in factura.items()
        if key not in GROUP_KEY_EXCLUDE_COLUMNS
    }
    return tuple(sorted(key_data.items(), key=lambda item: item[0]))


def resolve_grouped_amount(values: List[Decimal]) -> Decimal | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None

    unique_values = set(present_values)
    if len(unique_values) == 1:
        return present_values[0]

    return sum(present_values, Decimal('0')).quantize(Decimal('0.01'))


def parse_factura_row(row: Dict[str, str], row_num: int) -> Dict[str, Any]:
    """Parsea una fila del CSV a un diccionario de factura."""

    factura = {
        'receptor_cuit': clean_cuit(row.get('receptor_cuit', '')),
        'tipo_comprobante': parse_int(row.get('tipo_comprobante'), 'tipo_comprobante'),
        'concepto': parse_int(row.get('concepto'), 'concepto'),
        'fecha_emision': parse_date(row.get('fecha_emision'), 'fecha_emision'),
        'importe_total': parse_decimal(row.get('importe_total'), 'importe_total'),
        'importe_neto': parse_decimal(row.get('importe_neto'), 'importe_neto'),
        'importe_iva': parse_decimal(row.get('importe_iva'), 'importe_iva'),
    }

    # Guardar valores declarados para cross-validation (T2)
    factura['_declared_importe_total'] = factura['importe_total']
    factura['_declared_importe_neto'] = factura['importe_neto']
    factura['_declared_importe_iva'] = factura['importe_iva']

    # Campos opcionales
    if row.get('fecha_desde'):
        factura['fecha_desde'] = parse_date(row.get('fecha_desde'), 'fecha_desde')
    if row.get('fecha_hasta'):
        factura['fecha_hasta'] = parse_date(row.get('fecha_hasta'), 'fecha_hasta')
    if row.get('fecha_vto_pago'):
        factura['fecha_vto_pago'] = parse_date(row.get('fecha_vto_pago'), 'fecha_vto_pago')

    # moneda y cotizacion se ignoran silenciosamente (ya no se usan)

    # Email override fields (optional)
    emails_cc_raw = (row.get('emails_cc') or '').strip()
    if emails_cc_raw:
        factura['emails_cc'] = _validate_emails_cc(emails_cc_raw)
    email_asunto = (row.get('email_asunto') or '').strip()
    if email_asunto:
        factura['email_asunto'] = email_asunto
    email_mensaje = (row.get('email_mensaje') or '').strip()
    if email_mensaje:
        factura['email_mensaje'] = email_mensaje
    email_firma = (row.get('email_firma') or '').strip()
    if email_firma:
        factura['email_firma'] = email_firma

    # email_mensaje y email_firma sin email_asunto no tienen sentido
    if not factura.get('email_asunto') and (factura.get('email_mensaje') or factura.get('email_firma')):
        factura['_email_override_warning'] = 'email_mensaje y email_firma se ignoran sin email_asunto'
        factura.pop('email_mensaje', None)
        factura.pop('email_firma', None)

    # Comprobante asociado (para notas de crédito/débito)
    if row.get('cbte_asoc_tipo'):
        factura['cbte_asoc_tipo'] = parse_int(row.get('cbte_asoc_tipo'), 'cbte_asoc_tipo')
    if row.get('cbte_asoc_pto_vta'):
        factura['cbte_asoc_pto_vta'] = parse_int(row.get('cbte_asoc_pto_vta'), 'cbte_asoc_pto_vta')
    if row.get('cbte_asoc_nro'):
        factura['cbte_asoc_nro'] = parse_int(row.get('cbte_asoc_nro'), 'cbte_asoc_nro')

    # Items (siempre requeridos)
    item_descripcion = (row.get('item_descripcion') or '').strip()
    if not item_descripcion:
        raise ValueError("Campo 'item_descripcion' es requerido y no puede estar vacío")

    item_cantidad_raw = (row.get('item_cantidad') or '').strip()
    item_precio_raw = (row.get('item_precio_unitario') or '').strip()

    factura['items'] = [{
        'descripcion': item_descripcion,
        'cantidad': parse_decimal(item_cantidad_raw, 'item_cantidad') if item_cantidad_raw else Decimal('1'),
        'precio_unitario': parse_decimal(item_precio_raw, 'item_precio_unitario') if item_precio_raw else Decimal('0'),
    }]

    fecha_emision = factura['fecha_emision']
    factura['fecha_desde'] = factura.get('fecha_desde') or fecha_emision
    factura['fecha_hasta'] = factura.get('fecha_hasta') or fecha_emision
    factura['fecha_vto_pago'] = factura.get('fecha_vto_pago') or fecha_emision

    return factura


def clean_cuit(cuit: str) -> str:
    """Limpia el CUIT removiendo guiones y espacios."""
    return cuit.replace('-', '').replace(' ', '').strip()


def parse_int(value: str, field_name: str) -> int:
    """Parsea un valor a entero."""
    if not value or not value.strip():
        raise ValueError(f"Campo '{field_name}' es requerido")
    try:
        return int(value.strip())
    except ValueError:
        raise ValueError(f"Campo '{field_name}' debe ser un número entero")


def parse_decimal(value: str, field_name: str) -> Decimal:
    """Parsea un valor a Decimal."""
    if not value or not value.strip():
        raise ValueError(f"Campo '{field_name}' es requerido")
    try:
        # Soporta tanto punto como coma decimal
        cleaned = value.strip().replace(',', '.')
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Campo '{field_name}' debe ser un número decimal")


def parse_date(value: str, field_name: str) -> datetime:
    """Parsea un valor a fecha. Soporta formatos YYYY-MM-DD y DD/MM/YYYY."""
    if not value or not value.strip():
        raise ValueError(f"Campo '{field_name}' es requerido")

    value = value.strip()

    # Intentar formato ISO
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        pass

    # Intentar formato DD/MM/YYYY
    try:
        return datetime.strptime(value, '%d/%m/%Y').date()
    except ValueError:
        pass

    raise ValueError(f"Campo '{field_name}' debe tener formato YYYY-MM-DD o DD/MM/YYYY")


def _validate_emails_cc(value: str) -> str:
    """Valida y normaliza emails_cc: formato email, máximo 10 direcciones."""
    emails = [e.strip() for e in value.split(',') if e.strip()]
    if len(emails) > MAX_CC_EMAILS:
        raise ValueError(f'emails_cc: máximo {MAX_CC_EMAILS} direcciones')
    for email in emails:
        if not EMAIL_RE.match(email):
            raise ValueError(f'emails_cc: formato inválido: {email}')
    return ','.join(emails)
