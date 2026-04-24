import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple, Optional


# ---------------------------------------------------------------------------
# Column mapping: Excel header names → internal field names
# ---------------------------------------------------------------------------
HEADER_MAP = {
    'cuit': 'receptor_cuit',
    'tipo_comp': 'tipo_comprobante',
    'detalle factura': 'item_descripcion',
    'neto_uni': 'item_precio_unitario',
    'cant': 'item_cantidad',
    'neto_total': 'importe_neto',
    'iva': 'importe_iva',
    'total': 'importe_total',
    'mail': 'email_override',
    'mensaje_mail': 'email_mensaje',
    'asunto_mail': 'email_asunto',
    'emision_comp': 'fecha_emision',
    'nro_fac': 'cbte_asoc_nro',
}

# ---------------------------------------------------------------------------
# TIPO_COMP letter codes → ARCA numeric codes
# ---------------------------------------------------------------------------
TIPO_COMP_LETTER_MAP = {
    'A': 1, 'B': 6, 'C': 11,
    'NCA': 3, 'NCB': 8, 'NCC': 13,
    'NDA': 2, 'NDB': 7, 'NDC': 12,
}

# NC/ND → corresponding Factura type (for cbte_asoc_tipo auto-derivation)
NOTA_TO_FACTURA_MAP = {
    3: 1, 8: 6, 13: 11,   # NC A→FA A, NC B→FA B, NC C→FA C
    2: 1, 7: 6, 12: 11,   # ND A→FA A, ND B→FA B, ND C→FA C
}

# Types that are NC or ND (need comprobante asociado)
TIPOS_NOTA = {2, 3, 7, 8, 12, 13}

# ---------------------------------------------------------------------------
# Required / optional / grouping columns
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    'receptor_cuit',
    'tipo_comprobante',
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
    '_validation_warning',
    'email_override',
    'emails_cc',
    'email_asunto',
    'email_mensaje',
    'email_firma',
}

OPTIONAL_COLUMNS = [
    'concepto',
    'fecha_desde',
    'fecha_hasta',
    'fecha_vto_pago',
    'cbte_asoc_tipo',
    'cbte_asoc_pto_vta',
    'cbte_asoc_nro',
    'email_override',
    'emails_cc',
    'email_asunto',
    'email_mensaje',
    'email_firma',
]

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
MAX_CC_EMAILS = 10


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

def detect_delimiter(content: str) -> str:
    """Detect CSV delimiter by analyzing the first few lines.

    Heuristic: count `;` and `,` in the header line. The structural
    separator appears many more times than the other character.
    If the file uses `;` as delimiter, commas may still appear inside
    values (e.g. Argentine decimals), but they won't be as frequent
    as the actual delimiter.
    """
    first_line = content.split('\n', 1)[0]
    semicolons = first_line.count(';')
    commas = first_line.count(',')

    if semicolons > commas:
        return ';'
    return ','


def detect_number_format(content: str, delimiter: str) -> str:
    """Detect number format based on delimiter and content analysis.

    Returns:
        'ar' for Argentine format (1.234.567,89 — dot=thousands, comma=decimal)
        'en' for Anglo format (1234567.89 — dot=decimal)

    Heuristic: when delimiter is `;`, numbers likely use Argentine format.
    Additionally, we scan for the pattern `digits.digits.digits` which is
    unambiguously Argentine thousands formatting.
    """
    if delimiter == ';':
        return 'ar'

    # Even with comma delimiter, check if content has Argentine-style numbers
    # Pattern: digit(s).digit(s).digit(s) = at least two dots in a number = thousands
    ar_pattern = re.compile(r'\d{1,3}\.\d{3}\.\d{3}')
    sample = content[:5000]
    if ar_pattern.search(sample):
        return 'ar'

    return 'en'


def normalize_headers(headers: List[str]) -> List[str]:
    """Normalize CSV headers: strip BOM, whitespace, lowercase, then map
    Excel column names to internal field names.

    Unknown headers pass through unchanged (they'll be ignored by the parser).
    """
    normalized = []
    for i, h in enumerate(headers):
        if h is None:
            normalized.append(f'_unknown_{i}')
            continue
        clean = h.strip().lower()
        # Strip BOM from first header
        if i == 0:
            clean = clean.lstrip('\ufeff')
        mapped = HEADER_MAP.get(clean, clean)
        normalized.append(mapped)
    return normalized


# ---------------------------------------------------------------------------
# Type resolution
# ---------------------------------------------------------------------------

def resolve_tipo_comprobante(value: str) -> int:
    """Resolve tipo_comprobante from letter code or numeric value.

    Accepts: 'A', 'NCA', 'nca', '1', '3', etc.
    """
    if not value or not value.strip():
        raise ValueError("Campo 'tipo_comprobante' es requerido")

    cleaned = value.strip().upper()

    # Try letter code first
    if cleaned in TIPO_COMP_LETTER_MAP:
        return TIPO_COMP_LETTER_MAP[cleaned]

    # Try numeric
    try:
        code = int(cleaned)
        if code in NOTA_TO_FACTURA_MAP or code in {1, 6, 11, 51, 52, 53}:
            return code
        raise ValueError(f"Código de comprobante '{code}' no reconocido")
    except ValueError as e:
        if 'no reconocido' in str(e):
            raise
        raise ValueError(
            f"Campo 'tipo_comprobante' debe ser un código válido "
            f"(A, B, C, NCA, NCB, NCC, NDA, NDB, NDC o numérico)"
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def clean_cuit(cuit: str) -> str:
    """Limpia el CUIT removiendo guiones y espacios."""
    return cuit.replace('-', '').replace(' ', '').strip()


def parse_int(value: str, field_name: str) -> int:
    """Parsea un valor a entero."""
    if not value or not value.strip():
        raise ValueError(f"Campo '{field_name}' es requerido")
    try:
        cleaned = value.strip().replace('.', '').replace(',', '')
        return int(float(cleaned))
    except (ValueError, OverflowError):
        raise ValueError(f"Campo '{field_name}' debe ser un número entero")


def parse_int_optional(value: Optional[str], field_name: str) -> Optional[int]:
    """Parsea un valor a entero, retorna None si vacío."""
    if not value or not value.strip():
        return None
    return parse_int(value, field_name)


def parse_decimal(value: str, field_name: str, number_format: str = 'en') -> Decimal:
    """Parsea un valor a Decimal, soportando formato argentino y anglosajón.

    Args:
        number_format: 'ar' = Argentine (1.234,56), 'en' = Anglo (1234.56)
    """
    if not value or not value.strip():
        raise ValueError(f"Campo '{field_name}' es requerido")
    try:
        cleaned = value.strip()
        if number_format == 'ar':
            # Argentine: dots are thousands, comma is decimal
            cleaned = cleaned.replace('.', '')
            cleaned = cleaned.replace(',', '.')
        else:
            # Anglo: comma could be decimal (legacy support)
            if ',' in cleaned and '.' not in cleaned:
                cleaned = cleaned.replace(',', '.')
            elif ',' in cleaned and '.' in cleaned:
                # 1,234.56 — comma is thousands
                cleaned = cleaned.replace(',', '')
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Campo '{field_name}' debe ser un número decimal")


def parse_decimal_optional(value: Optional[str], field_name: str,
                           number_format: str = 'en') -> Optional[Decimal]:
    """Parsea un valor a Decimal, retorna None si vacío."""
    if not value or not value.strip():
        return None
    return parse_decimal(value, field_name, number_format)


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


def _validate_email_list(value: str, field_name: str = 'email') -> str:
    """Valida y normaliza una lista de emails separados por coma.
    Máximo MAX_CC_EMAILS direcciones."""
    emails = [e.strip() for e in value.split(',') if e.strip()]
    if len(emails) > MAX_CC_EMAILS:
        raise ValueError(f'{field_name}: máximo {MAX_CC_EMAILS} direcciones')
    for email in emails:
        if not EMAIL_RE.match(email):
            raise ValueError(f'{field_name}: formato inválido: {email}')
    return ','.join(emails)


# ---------------------------------------------------------------------------
# Main parse pipeline
# ---------------------------------------------------------------------------

def parse_csv(file_content: str,
              concepto_default: Optional[int] = None,
              ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Parsea el contenido CSV y retorna facturas, errores y warnings.

    Auto-detecta delimitador (`,` vs `;`) y formato numérico (argentino vs anglo).
    Soporta tanto headers internos como headers de Excel exportado.

    Args:
        file_content: Contenido raw del CSV
        concepto_default: Concepto por defecto del facturador (fallback si CSV no lo trae)

    Returns:
        Tuple[List[Dict], List[str], List[str]]: (facturas, errores, warnings)
    """
    errors = []
    warnings = []
    grouped_facturas = {}
    grouped_order = []

    # Strip BOM
    if file_content.startswith('\ufeff'):
        file_content = file_content[1:]

    # Auto-detect format
    delimiter = detect_delimiter(file_content)
    number_format = detect_number_format(file_content, delimiter)

    try:
        reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
        raw_columns = reader.fieldnames or []

        # Normalize headers (Excel names → internal names)
        normalized = normalize_headers(raw_columns)
        reader.fieldnames = normalized

        # Check required columns (concepto is optional now)
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in normalized]
        if missing_columns:
            return [], [f"Columnas requeridas faltantes: {', '.join(missing_columns)}"], []

        has_concepto_column = 'concepto' in normalized

        for row_num, row in enumerate(reader, start=2):
            try:
                factura = parse_factura_row(
                    row, row_num,
                    number_format=number_format,
                    concepto_default=concepto_default,
                    has_concepto_column=has_concepto_column,
                )
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
        return [], [f"Error al parsear CSV: {str(e)}"], []

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

        # Cross-validation: comparar declarados vs calculados → WARNING (not error)
        cross_warning = _cross_validate_importes(factura)
        if cross_warning:
            warnings.append(cross_warning)
            factura['_validation_warning'] = cross_warning

        # Keep _validation_error only for real errors (e.g. missing IVA on tipo A/B)
        recalc_error = factura.get('_validation_error')
        if recalc_error:
            factura['_validation_error'] = recalc_error

        facturas.append(factura)

    return facturas, errors, warnings


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------

def parse_factura_row(row: Dict[str, str], row_num: int, *,
                      number_format: str = 'en',
                      concepto_default: Optional[int] = None,
                      has_concepto_column: bool = True,
                      ) -> Optional[Dict[str, Any]]:
    """Parsea una fila del CSV a un diccionario de factura.

    Returns None for empty rows (no CUIT).
    """
    # Skip empty rows
    raw_cuit = (row.get('receptor_cuit') or '').strip()
    if not raw_cuit:
        return None

    factura = {
        'receptor_cuit': clean_cuit(raw_cuit),
        'tipo_comprobante': resolve_tipo_comprobante(row.get('tipo_comprobante', '')),
        'fecha_emision': parse_date(row.get('fecha_emision', ''), 'fecha_emision'),
        'importe_total': parse_decimal(row.get('importe_total', ''), 'importe_total', number_format),
        'importe_neto': parse_decimal(row.get('importe_neto', ''), 'importe_neto', number_format),
        'importe_iva': parse_decimal(row.get('importe_iva', ''), 'importe_iva', number_format),
    }

    # Concepto: from CSV column or facturador default.
    # The Excel template has a 'CONCEPTO' column that contains free text (e.g. "Balance 2025"),
    # NOT the ARCA concept code. We detect this by checking if the value is a valid code (1, 2, 3).
    concepto_resolved = False
    if has_concepto_column:
        concepto_raw = (row.get('concepto') or '').strip()
        if concepto_raw:
            try:
                concepto_val = int(concepto_raw)
                if concepto_val in (1, 2, 3):
                    factura['concepto'] = concepto_val
                    concepto_resolved = True
            except (ValueError, OverflowError):
                pass  # Non-numeric → treat as free text, ignore

    if not concepto_resolved:
        if concepto_default is not None:
            factura['concepto'] = concepto_default
        else:
            raise ValueError("Campo 'concepto' es requerido (no está en CSV ni configurado en facturador)")

    # Guardar valores declarados para cross-validation
    factura['_declared_importe_total'] = factura['importe_total']
    factura['_declared_importe_neto'] = factura['importe_neto']
    factura['_declared_importe_iva'] = factura['importe_iva']

    # Campos opcionales de fecha
    if row.get('fecha_desde'):
        factura['fecha_desde'] = parse_date(row.get('fecha_desde'), 'fecha_desde')
    if row.get('fecha_hasta'):
        factura['fecha_hasta'] = parse_date(row.get('fecha_hasta'), 'fecha_hasta')
    if row.get('fecha_vto_pago'):
        factura['fecha_vto_pago'] = parse_date(row.get('fecha_vto_pago'), 'fecha_vto_pago')

    # Email override (replaces receptor.email as TO)
    email_override_raw = (row.get('email_override') or '').strip()
    if email_override_raw:
        factura['email_override'] = _validate_email_list(email_override_raw, 'email_override')

    # Legacy: emails_cc (additional CC recipients)
    emails_cc_raw = (row.get('emails_cc') or '').strip()
    if emails_cc_raw:
        factura['emails_cc'] = _validate_email_list(emails_cc_raw, 'emails_cc')

    # Email subject/message (optional)
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

    # Comprobante asociado
    tipo = factura['tipo_comprobante']
    cbte_asoc_nro_raw = (row.get('cbte_asoc_nro') or '').strip()
    cbte_asoc_tipo_raw = (row.get('cbte_asoc_tipo') or '').strip()
    cbte_asoc_pto_vta_raw = (row.get('cbte_asoc_pto_vta') or '').strip()

    if cbte_asoc_tipo_raw or cbte_asoc_pto_vta_raw:
        # Explicit cbte_asoc fields (legacy format) — use as-is
        if cbte_asoc_tipo_raw:
            factura['cbte_asoc_tipo'] = parse_int(cbte_asoc_tipo_raw, 'cbte_asoc_tipo')
        if cbte_asoc_pto_vta_raw:
            factura['cbte_asoc_pto_vta'] = parse_int(cbte_asoc_pto_vta_raw, 'cbte_asoc_pto_vta')
        if cbte_asoc_nro_raw:
            factura['cbte_asoc_nro'] = parse_int(cbte_asoc_nro_raw, 'cbte_asoc_nro')
    elif tipo in TIPOS_NOTA and cbte_asoc_nro_raw:
        # NC/ND with NRO_FAC only (Excel format) — auto-derive tipo
        factura['cbte_asoc_nro'] = parse_int(cbte_asoc_nro_raw, 'cbte_asoc_nro')
        factura['cbte_asoc_tipo'] = NOTA_TO_FACTURA_MAP.get(tipo, tipo)
        # cbte_asoc_pto_vta will be filled from facturador in the API layer
    elif tipo not in TIPOS_NOTA and cbte_asoc_nro_raw:
        # NRO_FAC on a non-NC/ND type — ignore silently
        pass

    # Items (siempre requeridos)
    item_descripcion = (row.get('item_descripcion') or '').strip()
    if not item_descripcion:
        raise ValueError("Campo 'item_descripcion' es requerido y no puede estar vacío")

    item_cantidad_raw = (row.get('item_cantidad') or '').strip()
    item_precio_raw = (row.get('item_precio_unitario') or '').strip()

    factura['items'] = [{
        'descripcion': item_descripcion,
        'cantidad': parse_decimal(item_cantidad_raw, 'item_cantidad', number_format) if item_cantidad_raw else Decimal('1'),
        'precio_unitario': parse_decimal(item_precio_raw, 'item_precio_unitario', number_format) if item_precio_raw else Decimal('0'),
    }]

    fecha_emision = factura['fecha_emision']
    factura['fecha_desde'] = factura.get('fecha_desde') or fecha_emision
    factura['fecha_hasta'] = factura.get('fecha_hasta') or fecha_emision
    factura['fecha_vto_pago'] = factura.get('fecha_vto_pago') or fecha_emision

    return factura


# ---------------------------------------------------------------------------
# Grouping / recalculation / validation (mostly unchanged)
# ---------------------------------------------------------------------------

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

    Returns warning message string if mismatch, None if OK.
    Tolerance: Decimal('0.05') to absorb rounding artifacts from Excel formulas.
    """
    tolerance = Decimal('0.05')

    declared_total = factura.get('_declared_importe_total')
    declared_neto = factura.get('_declared_importe_neto')
    declared_iva = factura.get('_declared_importe_iva')

    computed_total = factura['importe_total']
    computed_neto = factura['importe_neto']
    computed_iva = factura['importe_iva']

    mismatches = []

    if declared_total is not None and abs(computed_total - declared_total) > tolerance:
        mismatches.append(f"importe_total declarado ({declared_total}) != calculado ({computed_total})")

    if declared_neto is not None and abs(computed_neto - declared_neto) > tolerance:
        mismatches.append(f"importe_neto declarado ({declared_neto}) != calculado ({computed_neto})")

    if declared_iva is not None and abs(computed_iva - declared_iva) > tolerance:
        mismatches.append(f"importe_iva declarado ({declared_iva}) != calculado ({computed_iva})")

    return "; ".join(mismatches) if mismatches else None
