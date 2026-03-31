def build_comprobante_pdf_filename(factura) -> str:
    """Construye nombre estandar de PDF de comprobante.

    Formato: cuit_idComprobante_PtoVenta_NroComp.pdf
    """
    facturador_cuit = _only_digits(getattr(getattr(factura, 'facturador', None), 'cuit', ''))
    tipo_comprobante = int(getattr(factura, 'tipo_comprobante', 0) or 0)
    punto_venta = int(getattr(factura, 'punto_venta', 0) or 0)
    numero = int(getattr(factura, 'numero_comprobante', 0) or 0)

    return f'{facturador_cuit:011d}_{tipo_comprobante:03d}_{punto_venta:05d}_{numero:08d}.pdf'


def _only_digits(value: str | None) -> int:
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return 0
    return int(digits)
