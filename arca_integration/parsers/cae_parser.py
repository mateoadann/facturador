from datetime import datetime
from typing import Optional, List
from ..types import CAEResponse


class CAEParser:
    """
    Parser para respuestas de CAE de ARCA.
    """

    @staticmethod
    def parse(response: dict) -> CAEResponse:
        """
        Parsea la respuesta de FECAESolicitar.

        Args:
            response: Respuesta raw de ARCA

        Returns:
            CAEResponse con los datos parseados
        """
        resultado = response.get('resultado', 'R')
        cae = response.get('cae')
        cae_vencimiento = CAEParser._parse_fecha(response.get('cae_vencimiento'))
        numero_comprobante = response.get('numero_comprobante')

        errores = []
        if response.get('errores'):
            errores = [
                {'code': e.get('code'), 'message': e.get('msg')}
                for e in response['errores']
            ]

        observaciones = []
        if response.get('observaciones'):
            observaciones = [
                {'code': o.get('code'), 'message': o.get('msg')}
                for o in response['observaciones']
            ]

        return CAEResponse(
            resultado=resultado,
            cae=cae,
            cae_vencimiento=cae_vencimiento,
            numero_comprobante=numero_comprobante,
            errores=errores,
            observaciones=observaciones
        )

    @staticmethod
    def _parse_fecha(fecha_str: Optional[str]):
        """Parsea fecha de formato ARCA."""
        if not fecha_str:
            return None
        try:
            return datetime.strptime(str(fecha_str), '%Y%m%d').date()
        except ValueError:
            return None

    @staticmethod
    def format_error_message(errors: List[dict]) -> str:
        """Formatea lista de errores en un mensaje legible."""
        if not errors:
            return ''
        messages = [f"[{e.get('code', '?')}] {e.get('message', 'Error desconocido')}" for e in errors]
        return '; '.join(messages)
