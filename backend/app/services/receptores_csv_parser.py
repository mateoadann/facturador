import csv
import io
import re
from typing import Any


HEADER_ALIASES = {
    'cuit': 'doc_nro',
    'cuit/cuil': 'doc_nro',
    'cuit_cuil': 'doc_nro',
    'doc_nro': 'doc_nro',
    'doc nro': 'doc_nro',
    'documento': 'doc_nro',
    'razon_social': 'razon_social',
    'razon social': 'razon_social',
    'razón social': 'razon_social',
    'condicion_iva': 'condicion_iva',
    'condicion iva': 'condicion_iva',
    'condición iva': 'condicion_iva',
    'email': 'email',
    'correo': 'email',
    'direccion': 'direccion',
    'dirección': 'direccion',
    'domicilio': 'direccion',
}

REQUIRED_CANONICAL_HEADERS = ['doc_nro', 'razon_social']


def parse_receptores_csv(file_bytes: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """Parsea CSV de receptores y retorna filas válidas + errores por fila."""
    content = _decode_csv(file_bytes)
    reader = csv.DictReader(io.StringIO(content))

    raw_headers = reader.fieldnames or []
    normalized_header_map = _normalize_headers(raw_headers)

    missing = [h for h in REQUIRED_CANONICAL_HEADERS if h not in normalized_header_map.values()]
    if missing:
        missing_labels = ', '.join(missing)
        raise ValueError(f'Columnas requeridas faltantes: {missing_labels}')

    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for row_num, raw_row in enumerate(reader, start=2):
        try:
            parsed = _parse_row(raw_row, normalized_header_map)
            rows.append(parsed)
        except ValueError as exc:
            errors.append(f'Fila {row_num}: {str(exc)}')

    return rows, errors


def _decode_csv(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return file_bytes.decode('latin-1')
        except UnicodeDecodeError as exc:
            raise ValueError('No se pudo decodificar el archivo CSV') from exc


def _normalize_headers(raw_headers: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in raw_headers:
        key = _normalize_header_key(raw)
        canonical = HEADER_ALIASES.get(key)
        if canonical:
            result[raw] = canonical
    return result


def _normalize_header_key(header: str) -> str:
    cleaned = (header or '').strip().lower()
    cleaned = cleaned.replace('-', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned


def _parse_row(raw_row: dict[str, str], header_map: dict[str, str]) -> dict[str, Any]:
    canonical_row = {
        canonical: (raw_row.get(raw_header) or '').strip()
        for raw_header, canonical in header_map.items()
    }

    doc_nro = _clean_cuit(canonical_row.get('doc_nro', ''))
    if not doc_nro:
        raise ValueError("Campo 'cuit' es requerido")
    if not doc_nro.isdigit() or len(doc_nro) != 11:
        raise ValueError("Campo 'cuit' debe tener 11 dígitos")

    razon_social = canonical_row.get('razon_social', '').strip()
    if not razon_social:
        raise ValueError("Campo 'razon_social' es requerido")

    email = canonical_row.get('email', '').strip() or None
    if email and not _is_valid_email(email):
        raise ValueError("Campo 'email' inválido")

    condicion_iva = canonical_row.get('condicion_iva', '').strip() or None
    direccion = canonical_row.get('direccion', '').strip() or None

    return {
        'doc_tipo': 80,
        'doc_nro': doc_nro,
        'razon_social': razon_social,
        'condicion_iva': condicion_iva,
        'email': email,
        'direccion': direccion,
    }


def _clean_cuit(value: str) -> str:
    return value.replace('-', '').replace(' ', '').strip()


def _is_valid_email(email: str) -> bool:
    # Validación básica para evitar falsos positivos obvios.
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) is not None
