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
    'condicion_iva_id': 'condicion_iva_id',
    'condicion iva id': 'condicion_iva_id',
    'condición iva id': 'condicion_iva_id',
    'id condicion iva': 'condicion_iva_id',
    'email': 'email',
    'correo': 'email',
    'direccion': 'direccion',
    'dirección': 'direccion',
    'domicilio': 'direccion',
}

# Mapping de nombres a IDs para compatibilidad con CSV
NOMBRE_A_ID = {
    'iva responsable inscripto': 1,
    'responsable inscripto': 1,
    'ri': 1,
    '1': 1,
    'iva sujeto exento': 4,
    'iva exento': 4,
    'exento': 4,
    '4': 4,
    'consumidor final': 5,
    'consumidor': 5,
    'cf': 5,
    '5': 5,
    'responsable monotributo': 6,
    'monotributista': 6,
    'monotributo': 6,
    '6': 6,
    'sujeto no categorizado': 7,
    'no categorizado': 7,
    '7': 7,
    'proveedor del exterior': 8,
    '8': 8,
    'cliente del exterior': 9,
    '9': 9,
    'iva liberado': 10,
    'iva liberado ley 19.640': 10,
    '10': 10,
    'monotributista social': 13,
    '13': 13,
    'iva no alcanzado': 15,
    '15': 15,
    'monotributo trabajador independiente promovido': 16,
    '16': 16,
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

    # Resolver condicion_iva_id desde nombre o ID directo
    condicion_iva_id = None
    raw_condicion_iva = canonical_row.get('condicion_iva', '').strip()
    raw_condicion_iva_id = canonical_row.get('condicion_iva_id', '').strip()
    
    if raw_condicion_iva_id:
        # ID directo en CSV
        try:
            condicion_iva_id = int(raw_condicion_iva_id)
        except ValueError:
            pass
    elif raw_condicion_iva:
        # Nombre en CSV, convertir a ID
        condicion_iva_id = NOMBRE_A_ID.get(raw_condicion_iva.lower())
    
    direccion = canonical_row.get('direccion', '').strip() or None

    return {
        'doc_tipo': 80,
        'doc_nro': doc_nro,
        'razon_social': razon_social,
        'condicion_iva_id': condicion_iva_id,
        'email': email,
        'direccion': direccion,
    }


def _clean_cuit(value: str) -> str:
    return value.replace('-', '').replace(' ', '').strip()


def _is_valid_email(email: str) -> bool:
    # Validación básica para evitar falsos positivos obvios.
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) is not None
