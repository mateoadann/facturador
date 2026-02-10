from datetime import datetime
from typing import Optional
from ..exceptions import ArcaError


class WSFEService:
    """
    Servicio de alto nivel para interactuar con WSFE (Facturación Electrónica).
    Provee métodos simplificados sobre ArcaClient.
    """

    def __init__(self, client):
        self.client = client

    def autorizar(self, request_data: dict) -> dict:
        """
        Autoriza un comprobante y obtiene el CAE.

        Args:
            request_data: Datos del comprobante generados por FacturaBuilder.build()

        Returns:
            Diccionario con resultado de la autorización:
            - success: True/False
            - cae: Código de Autorización Electrónica
            - cae_vencimiento: Fecha de vencimiento del CAE (ISO format)
            - numero_comprobante: Número asignado al comprobante
            - observaciones: Lista de observaciones de ARCA
            - error_code: Código de error (si falló)
            - error_message: Mensaje de error (si falló)
        """
        try:
            result = self.client.fe_cae_solicitar(request_data)

            if result.get('resultado') == 'A':
                return {
                    'success': True,
                    'cae': result.get('cae'),
                    'cae_vencimiento': self._parse_fecha(result.get('cae_vencimiento')),
                    'numero_comprobante': result.get('numero_comprobante'),
                    'observaciones': result.get('observaciones', []),
                }
            else:
                errores = result.get('errores', [])
                observaciones = result.get('observaciones', [])
                # Los errores pueden venir como errores o como observaciones de rechazo
                all_messages = errores + observaciones
                error_msg = '; '.join([e.get('msg', '') for e in all_messages if e.get('msg')])
                return {
                    'success': False,
                    'error_code': errores[0].get('code') if errores else None,
                    'error_message': error_msg or 'Error desconocido al autorizar comprobante',
                    'errores': errores,
                    'observaciones': observaciones,
                }

        except ArcaError:
            raise
        except Exception as e:
            raise ArcaError(f'Error al autorizar comprobante: {str(e)}')

    def consultar_comprobante(
        self,
        tipo_cbte: int,
        punto_venta: int,
        numero: int
    ) -> dict:
        """
        Consulta un comprobante ya autorizado en ARCA.

        Args:
            tipo_cbte: Tipo de comprobante (1=FC A, 6=FC B, etc.)
            punto_venta: Punto de venta
            numero: Número de comprobante

        Returns:
            Datos del comprobante consultado
        """
        result = self.client.fe_comp_consultar(
            tipo_cbte=tipo_cbte,
            punto_venta=punto_venta,
            numero=numero,
        )

        if isinstance(result, dict) and result.get('encontrado'):
            result = {
                **result,
                'fecha_cbte': self._parse_fecha(result.get('fecha_cbte')),
                'cae_vto': self._parse_fecha(result.get('cae_vto')),
            }

        return result

    def ultimo_autorizado(self, punto_venta: int, tipo_cbte: int) -> int:
        """
        Obtiene el último número de comprobante autorizado.

        Args:
            punto_venta: Punto de venta
            tipo_cbte: Tipo de comprobante

        Returns:
            Número del último comprobante autorizado
        """
        return self.client.fe_comp_ultimo_autorizado(
            punto_venta=punto_venta,
            tipo_cbte=tipo_cbte,
        )

    def _parse_fecha(self, fecha_str: Optional[str]) -> Optional[str]:
        """Parsea fecha de formato ARCA (YYYYMMDD) a ISO."""
        if not fecha_str:
            return None
        try:
            dt = datetime.strptime(str(fecha_str), '%Y%m%d')
            return dt.date().isoformat()
        except ValueError:
            return str(fecha_str)
