from decimal import Decimal, ROUND_HALF_UP

from arca_integration.constants import (
    TIPOS_COMPROBANTE_C,
    TIPO_CBTE_CLASE,
    CONDICIONES_IVA_POR_CLASE,
)


def es_comprobante_tipo_c(tipo_comprobante: int | None) -> bool:
    if tipo_comprobante is None:
        return False
    return int(tipo_comprobante) in TIPOS_COMPROBANTE_C


def es_comprobante_tipo_a(tipo_comprobante: int | None) -> bool:
    if tipo_comprobante is None:
        return False
    return TIPO_CBTE_CLASE.get(int(tipo_comprobante)) == 'A'


def es_comprobante_tipo_b(tipo_comprobante: int | None) -> bool:
    if tipo_comprobante is None:
        return False
    return TIPO_CBTE_CLASE.get(int(tipo_comprobante)) == 'B'


def get_clase_comprobante(tipo_comprobante: int | None) -> str | None:
    if tipo_comprobante is None:
        return None
    return TIPO_CBTE_CLASE.get(int(tipo_comprobante))


def es_condicion_iva_valida_para_tipo(condicion_iva: int, tipo_comprobante: int) -> tuple[bool, str]:
    """
    Valida que la condición IVA del receptor sea compatible con el tipo de comprobante.
    
    Returns:
        (is_valid, error_message)
    """
    if condicion_iva is None or tipo_comprobante is None:
        return True, ""
    
    clase = get_clase_comprobante(tipo_comprobante)
    if clase is None:
        return True, ""
    
    condiciones_validas = CONDICIONES_IVA_POR_CLASE.get(clase, set())
    
    if condicion_iva not in condiciones_validas:
        condiciones_str = ", ".join(sorted(condiciones_validas))
        return False, (
            f"Condición IVA {condicion_iva} no válida para comprobante clase {clase}. "
            f"Valores permitidos: {condiciones_str}"
        )
    
    return True, ""


def normalizar_importes_para_tipo_c(
    tipo_comprobante: int | None,
    importe_neto: Decimal | int | float | None,
    importe_iva: Decimal | int | float | None,
    importe_total: Decimal | int | float | None,
) -> tuple[Decimal, Decimal, Decimal]:
    neto = Decimal(str(importe_neto or 0)).quantize(Decimal('0.01'))
    iva = Decimal(str(importe_iva or 0)).quantize(Decimal('0.01'))
    total = Decimal(str(importe_total or 0)).quantize(Decimal('0.01'))

    if es_comprobante_tipo_c(tipo_comprobante):
        iva = Decimal('0.00')
        total = neto
    
    # Factura B: siempre discriminar IVA (RG 5614 - Transparencia Fiscal)
    # El IVA está incluido en el total, se calcula y discrimina
    if es_comprobante_tipo_b(tipo_comprobante):
        if iva == Decimal('0.00') and total > 0:
            # Calcular IVA desde el total (21%)
            iva = (total / Decimal('1.21') * Decimal('0.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            neto = total - iva

    return neto, iva, total
