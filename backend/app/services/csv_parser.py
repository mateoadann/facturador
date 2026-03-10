import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple


REQUIRED_COLUMNS = [
    'facturador_cuit',
    'receptor_cuit',
    'tipo_comprobante',
    'concepto',
    'fecha_emision',
    'importe_total',
    'importe_neto'
]

GROUP_KEY_EXCLUDE_COLUMNS = {
    'items',
    'importe_total',
    'importe_neto',
    'importe_iva',
}

OPTIONAL_COLUMNS = [
    'fecha_desde',
    'fecha_hasta',
    'fecha_vto_pago',
    'importe_iva',
    'moneda',
    'cotizacion',
    'cbte_asoc_tipo',
    'cbte_asoc_pto_vta',
    'cbte_asoc_nro'
]

ITEM_COLUMNS = [
    'item_descripcion',
    'item_cantidad',
    'item_precio_unitario',
]


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

                    if factura.get('items'):
                        grouped['items'].extend(factura['items'])
            except ValueError as e:
                errors.append(f"Fila {row_num}: {str(e)}")

    except csv.Error as e:
        return [], [f"Error al parsear CSV: {str(e)}"]

    facturas = []
    for key in grouped_order:
        grouped = grouped_facturas[key]
        factura = grouped['factura']

        if grouped['items']:
            factura['items'] = grouped['items']
            # Cuando hay items, recalcular importes desde los items
            factura = _recalculate_from_items(factura, grouped)
        else:
            # Sin items - usar importes directo del CSV
            factura['importe_total'] = resolve_grouped_amount(grouped['importe_total_rows'])
            factura['importe_neto'] = resolve_grouped_amount(grouped['importe_neto_rows'])

            importe_iva = resolve_grouped_amount(grouped['importe_iva_rows'])
            if importe_iva is not None:
                factura['importe_iva'] = importe_iva
                factura['items_sin_iva'] = False
            else:
                factura['importe_iva'] = Decimal('0')
                factura['items_sin_iva'] = True

        facturas.append(factura)

    return facturas, errors


def _recalculate_from_items(factura: Dict[str, Any], grouped: Dict) -> Dict[str, Any]:
    """Recalcula importes desde los items.
    
    Si viene importe_iva del CSV, se distribuye proporcionalmente por item.
    Si NO viene importe_iva, marca items_sin_iva = true.
    """
    items = factura['items']
    
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
        factura['items_sin_iva'] = False
    else:
        # No viene IVA - marcar como sin IVA
        for item in items:
            item['importe_iva'] = Decimal('0')
            item['importe_neto'] = item['subtotal']
        factura['importe_iva'] = Decimal('0')
        factura['items_sin_iva'] = True
    
    factura['importe_neto'] = importe_neto_total
    factura['importe_total'] = (importe_neto_total + factura['importe_iva']).quantize(Decimal('0.01'))

    return factura


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
        'facturador_cuit': clean_cuit(row.get('facturador_cuit', '')),
        'receptor_cuit': clean_cuit(row.get('receptor_cuit', '')),
        'tipo_comprobante': parse_int(row.get('tipo_comprobante'), 'tipo_comprobante'),
        'concepto': parse_int(row.get('concepto'), 'concepto'),
        'fecha_emision': parse_date(row.get('fecha_emision'), 'fecha_emision'),
        'importe_total': parse_decimal(row.get('importe_total'), 'importe_total'),
        'importe_neto': parse_decimal(row.get('importe_neto'), 'importe_neto'),
    }

    # Campos opcionales
    if row.get('fecha_desde'):
        factura['fecha_desde'] = parse_date(row.get('fecha_desde'), 'fecha_desde')
    if row.get('fecha_hasta'):
        factura['fecha_hasta'] = parse_date(row.get('fecha_hasta'), 'fecha_hasta')
    if row.get('fecha_vto_pago'):
        factura['fecha_vto_pago'] = parse_date(row.get('fecha_vto_pago'), 'fecha_vto_pago')
    if row.get('importe_iva'):
        factura['importe_iva'] = parse_decimal(row.get('importe_iva'), 'importe_iva')
    if row.get('moneda'):
        factura['moneda'] = row.get('moneda', 'PES')
    if row.get('cotizacion'):
        factura['cotizacion'] = parse_decimal(row.get('cotizacion'), 'cotizacion')

    # Comprobante asociado (para notas de crédito/débito)
    if row.get('cbte_asoc_tipo'):
        factura['cbte_asoc_tipo'] = parse_int(row.get('cbte_asoc_tipo'), 'cbte_asoc_tipo')
    if row.get('cbte_asoc_pto_vta'):
        factura['cbte_asoc_pto_vta'] = parse_int(row.get('cbte_asoc_pto_vta'), 'cbte_asoc_pto_vta')
    if row.get('cbte_asoc_nro'):
        factura['cbte_asoc_nro'] = parse_int(row.get('cbte_asoc_nro'), 'cbte_asoc_nro')

    # Items (si están presentes)
    if row.get('item_descripcion'):
        factura['items'] = [{
            'descripcion': row.get('item_descripcion'),
            'cantidad': parse_decimal(row.get('item_cantidad', '1'), 'item_cantidad'),
            'precio_unitario': parse_decimal(row.get('item_precio_unitario', '0'), 'item_precio_unitario'),
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
