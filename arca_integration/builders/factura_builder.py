from datetime import date
from decimal import Decimal
from typing import Optional, List
from ..exceptions import ArcaValidationError


class FacturaBuilder:
    """
    Builder para construir requests de facturación para ARCA.
    """

    def __init__(self):
        self._tipo_cbte: Optional[int] = None
        self._punto_venta: Optional[int] = None
        self._numero: Optional[int] = None
        self._concepto: Optional[int] = None
        self._fecha_emision: Optional[date] = None
        self._fecha_desde: Optional[date] = None
        self._fecha_hasta: Optional[date] = None
        self._fecha_vto_pago: Optional[date] = None
        self._doc_tipo: Optional[int] = None
        self._doc_nro: Optional[int] = None
        self._importe_total: Optional[Decimal] = None
        self._importe_neto: Optional[Decimal] = None
        self._importe_iva: Decimal = Decimal('0')
        self._importe_tributos: Decimal = Decimal('0')
        self._importe_no_gravado: Decimal = Decimal('0')
        self._importe_exento: Decimal = Decimal('0')
        self._moneda: str = 'PES'
        self._cotizacion: Decimal = Decimal('1')
        self._alicuotas_iva: List[dict] = []
        self._cbte_asoc_tipo: Optional[int] = None
        self._cbte_asoc_pto_vta: Optional[int] = None
        self._cbte_asoc_nro: Optional[int] = None
        self._condicion_iva_receptor_id: Optional[int] = None

    def set_comprobante(
        self,
        tipo: int,
        punto_venta: int,
        numero: int,
        concepto: int
    ) -> 'FacturaBuilder':
        """Configura los datos del comprobante."""
        self._tipo_cbte = tipo
        self._punto_venta = punto_venta
        self._numero = numero
        self._concepto = concepto
        return self

    def set_fechas(
        self,
        emision: date,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        vto_pago: Optional[date] = None
    ) -> 'FacturaBuilder':
        """Configura las fechas del comprobante."""
        self._fecha_emision = emision
        self._fecha_desde = desde
        self._fecha_hasta = hasta
        self._fecha_vto_pago = vto_pago
        return self

    def set_receptor(self, doc_tipo: int, doc_nro: str) -> 'FacturaBuilder':
        """Configura el receptor del comprobante."""
        nro = str(doc_nro).replace('-', '').replace(' ', '')
        if not nro.isdigit():
            raise ArcaValidationError('Número de documento del receptor inválido')

        self._doc_tipo = doc_tipo
        self._doc_nro = int(nro)
        return self

    def set_importes(
        self,
        total: float,
        neto: float,
        iva: float = 0,
        tributos: float = 0,
        no_gravado: float = 0,
        exento: float = 0
    ) -> 'FacturaBuilder':
        """Configura los importes del comprobante."""
        self._importe_total = Decimal(str(total))
        self._importe_neto = Decimal(str(neto))
        self._importe_iva = Decimal(str(iva))
        self._importe_tributos = Decimal(str(tributos))
        self._importe_no_gravado = Decimal(str(no_gravado))
        self._importe_exento = Decimal(str(exento))
        return self

    def set_moneda(self, moneda: str, cotizacion: float = 1) -> 'FacturaBuilder':
        """Configura la moneda del comprobante."""
        self._moneda = moneda
        self._cotizacion = Decimal(str(cotizacion))
        return self

    def add_iva(
        self,
        alicuota_id: int,
        base_imponible: float,
        importe: float
    ) -> 'FacturaBuilder':
        """Agrega una alícuota de IVA."""
        self._alicuotas_iva.append({
            'Id': alicuota_id,
            'BaseImp': round(base_imponible, 2),
            'Importe': round(importe, 2)
        })
        return self

    def set_comprobante_asociado(
        self,
        tipo: int,
        punto_venta: int,
        numero: int
    ) -> 'FacturaBuilder':
        """Configura el comprobante asociado (para NC/ND)."""
        self._cbte_asoc_tipo = tipo
        self._cbte_asoc_pto_vta = punto_venta
        self._cbte_asoc_nro = numero
        return self

    def set_condicion_iva_receptor(self, condicion_iva_id: int) -> 'FacturaBuilder':
        """Configura la condición IVA del receptor (RG 5616)."""
        self._condicion_iva_receptor_id = int(condicion_iva_id)
        return self

    def validate(self) -> bool:
        """Valida que todos los campos requeridos estén presentes."""
        if not self._tipo_cbte:
            raise ArcaValidationError('Tipo de comprobante es requerido')
        if not self._punto_venta:
            raise ArcaValidationError('Punto de venta es requerido')
        if not self._numero:
            raise ArcaValidationError('Número de comprobante es requerido')
        if not self._concepto:
            raise ArcaValidationError('Concepto es requerido')
        if not self._fecha_emision:
            raise ArcaValidationError('Fecha de emisión es requerida')
        if not self._doc_tipo:
            raise ArcaValidationError('Tipo de documento del receptor es requerido')
        if not self._doc_nro:
            raise ArcaValidationError('Número de documento del receptor es requerido')
        if self._importe_total is None:
            raise ArcaValidationError('Importe total es requerido')
        if self._importe_neto is None:
            raise ArcaValidationError('Importe neto es requerido')

        # Validar fechas para servicios
        if self._concepto in (2, 3):  # Servicios o Productos y Servicios
            if not self._fecha_desde or not self._fecha_hasta or not self._fecha_vto_pago:
                raise ArcaValidationError(
                    'Para servicios se requieren fecha_desde, fecha_hasta y fecha_vto_pago'
                )

        # Notas de crédito / débito requieren comprobante asociado
        tipos_nota = {2, 3, 7, 8, 12, 13, 52, 53}
        if self._tipo_cbte in tipos_nota:
            if not (self._cbte_asoc_tipo and self._cbte_asoc_pto_vta and self._cbte_asoc_nro):
                raise ArcaValidationError(
                    'Para notas de crédito/débito se requiere comprobante asociado (tipo, punto de venta y número)'
                )

        return True

    def build(self) -> dict:
        """Construye el request para ARCA."""
        self.validate()

        tipo_cbte = self._tipo_cbte
        punto_venta = self._punto_venta
        numero = self._numero
        concepto = self._concepto
        fecha_emision = self._fecha_emision
        doc_tipo = self._doc_tipo
        doc_nro = self._doc_nro
        importe_total = self._importe_total
        importe_neto = self._importe_neto

        if None in (tipo_cbte, punto_venta, numero, concepto, fecha_emision, doc_tipo, doc_nro, importe_total, importe_neto):
            raise ArcaValidationError('Datos incompletos para construir comprobante')

        assert tipo_cbte is not None
        assert punto_venta is not None
        assert numero is not None
        assert concepto is not None
        assert fecha_emision is not None
        assert doc_tipo is not None
        assert doc_nro is not None
        assert importe_total is not None
        assert importe_neto is not None

        # Formato de fecha ARCA: YYYYMMDD
        def format_date(d: date) -> str:
            return d.strftime('%Y%m%d')

        det_request = {
            'Concepto': concepto,
            'DocTipo': doc_tipo,
            'DocNro': doc_nro,
            'CbteDesde': numero,
            'CbteHasta': numero,
            'CbteFch': format_date(fecha_emision),
            'ImpTotal': float(importe_total),
            'ImpTotConc': float(self._importe_no_gravado),
            'ImpNeto': float(importe_neto),
            'ImpOpEx': float(self._importe_exento),
            'ImpTrib': float(self._importe_tributos),
            'ImpIVA': float(self._importe_iva),
            'MonId': self._moneda,
            'MonCotiz': float(self._cotizacion),
        }

        # Fechas de servicio
        if self._fecha_desde:
            det_request['FchServDesde'] = format_date(self._fecha_desde)
        if self._fecha_hasta:
            det_request['FchServHasta'] = format_date(self._fecha_hasta)
        if self._fecha_vto_pago:
            det_request['FchVtoPago'] = format_date(self._fecha_vto_pago)

        # Alícuotas de IVA
        if self._alicuotas_iva:
            det_request['Iva'] = {'AlicIva': self._alicuotas_iva}

        # Comprobante asociado
        if self._cbte_asoc_tipo:
            det_request['CbtesAsoc'] = {
                'CbteAsoc': [{
                    'Tipo': self._cbte_asoc_tipo,
                    'PtoVta': self._cbte_asoc_pto_vta,
                    'Nro': self._cbte_asoc_nro,
                }]
            }

        # RG 5616: condición frente al IVA del receptor
        if self._condicion_iva_receptor_id is not None:
            det_request['CondicionIVAReceptorId'] = self._condicion_iva_receptor_id

        return {
            'FeCAEReq': {
                'FeCabReq': {
                    'CantReg': 1,
                    'PtoVta': punto_venta,
                    'CbteTipo': tipo_cbte,
                },
                'FeDetReq': {
                    'FECAEDetRequest': [det_request]
                }
            }
        }
