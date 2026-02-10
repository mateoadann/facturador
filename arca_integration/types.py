from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List


@dataclass
class Comprobante:
    """Representa un comprobante de ARCA."""
    tipo: int
    punto_venta: int
    numero: int
    concepto: int
    fecha_emision: date
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    fecha_vto_pago: Optional[date] = None


@dataclass
class Receptor:
    """Representa un receptor de comprobante."""
    doc_tipo: int
    doc_nro: str


@dataclass
class Importes:
    """Representa los importes de un comprobante."""
    total: Decimal
    neto: Decimal
    iva: Decimal = Decimal('0')
    tributos: Decimal = Decimal('0')
    no_gravado: Decimal = Decimal('0')
    exento: Decimal = Decimal('0')


@dataclass
class AlicuotaIVA:
    """Representa una alícuota de IVA."""
    id: int
    base_imponible: Decimal
    importe: Decimal


@dataclass
class ComprobanteAsociado:
    """Representa un comprobante asociado (para NC/ND)."""
    tipo: int
    punto_venta: int
    numero: int
    cuit_emisor: Optional[str] = None
    fecha: Optional[date] = None


@dataclass
class FacturaRequest:
    """Request completo para solicitar CAE."""
    comprobante: Comprobante
    receptor: Receptor
    importes: Importes
    moneda: str = 'PES'
    cotizacion: Decimal = Decimal('1')
    alicuotas_iva: List[AlicuotaIVA] = field(default_factory=list)
    comprobante_asociado: Optional[ComprobanteAsociado] = None


@dataclass
class CAEResponse:
    """Respuesta de solicitud de CAE."""
    resultado: str
    cae: Optional[str] = None
    cae_vencimiento: Optional[date] = None
    numero_comprobante: Optional[int] = None
    errores: List[dict] = field(default_factory=list)
    observaciones: List[dict] = field(default_factory=list)
