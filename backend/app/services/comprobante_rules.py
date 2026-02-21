from decimal import Decimal


TIPOS_COMPROBANTE_C = {11, 12, 13}


def es_comprobante_tipo_c(tipo_comprobante: int | None) -> bool:
    if tipo_comprobante is None:
        return False
    return int(tipo_comprobante) in TIPOS_COMPROBANTE_C


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

    return neto, iva, total
