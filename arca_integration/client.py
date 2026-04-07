import tempfile
import os
import time
import pickle
import fcntl
import json
import ast
import re
import os
import ssl
import logging
import importlib
from contextlib import contextmanager
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

# AFIP/ARCA servers use small DH parameters that OpenSSL 3.x rejects by default.
# Patch SSLContext.wrap_socket to force SECLEVEL=1 on every TLS connection.
_orig_wrap_socket = ssl.SSLContext.wrap_socket


def _patched_wrap_socket(self, *args, **kwargs):
    try:
        self.set_ciphers('DEFAULT@SECLEVEL=1')
    except Exception:
        pass
    return _orig_wrap_socket(self, *args, **kwargs)


ssl.SSLContext.wrap_socket = _patched_wrap_socket

import arca_arg.settings as arca_settings
import arca_arg.auth as arca_auth
import arca_arg.webservice as arca_ws
from arca_arg.webservice import ArcaWebService
from arca_arg.settings import WSDL_FEV1_HOM, WSDL_FEV1_PROD, WSDL_CONSTANCIA_HOM, WSDL_CONSTANCIA_PROD

from .exceptions import ArcaError, ArcaAuthError


logger = logging.getLogger(__name__)


class ArcaClient:
    """
    Cliente wrapper para la librería arca_arg.
    Maneja la autenticación y conexión con los servicios de ARCA.

    La librería arca_arg usa configuración global via arca_arg.settings,
    así que este wrapper configura esos settings y luego crea las instancias
    de ArcaWebService necesarias.
    """

    def __init__(
        self,
        cuit: str,
        cert: bytes,
        key: bytes,
        ambiente: str = 'testing'
    ):
        self.cuit = cuit.replace('-', '')
        self.ambiente = ambiente
        self.is_production = ambiente == 'production'
        self.verbose_logs = os.getenv('ARCA_VERBOSE_LOGS', 'false').strip().lower() == 'true'
        self.verbose_format = (os.getenv('ARCA_VERBOSE_FORMAT', 'compact') or 'compact').strip().lower()
        self.verbose_include_raw = os.getenv('ARCA_VERBOSE_INCLUDE_RAW', 'false').strip().lower() == 'true'
        flask_env = (os.getenv('FLASK_ENV', 'development') or 'development').strip().lower()
        self.environment = 'dev' if flask_env.startswith('dev') else ('prod' if flask_env.startswith('prod') else flask_env)

        self._temp_dir = tempfile.mkdtemp()
        self._cert_path = os.path.join(self._temp_dir, 'cert.pem')
        self._key_path = os.path.join(self._temp_dir, 'key.key')

        # Cache estable de TA por CUIT/ambiente para evitar pedir login WSAA
        # en cada emisión (evita errores como "ya posee un TA válido").
        ta_cache_root = os.getenv('ARCA_TA_CACHE_DIR') or os.path.join(tempfile.gettempdir(), 'arca_ta_cache')
        ta_base_dir = os.path.join(ta_cache_root, self.ambiente, self.cuit)
        os.makedirs(ta_base_dir, exist_ok=True)
        if not ta_base_dir.endswith(os.sep):
            ta_base_dir = ta_base_dir + os.sep
        self._ta_path = ta_base_dir

        with open(self._cert_path, 'wb') as f:
            f.write(cert)
        with open(self._key_path, 'wb') as f:
            f.write(key)

        self._configure_settings()

        self._wsfe: Optional[ArcaWebService] = None
        self._ws_constancia: Optional[ArcaWebService] = None

    def _configure_settings(self):
        """Configura arca_arg.settings con los datos de esta instancia."""
        arca_settings.PRIVATE_KEY_PATH = self._key_path
        arca_settings.CERT_PATH = self._cert_path
        arca_settings.TA_FILES_PATH = self._ta_path
        arca_settings.CUIT = self.cuit
        arca_settings.PROD = self.is_production

        # arca_arg importa algunos settings por valor en otros módulos.
        # Para que tome la configuración dinámica, se actualizan también esos globals.
        arca_auth.PRIVATE_KEY_PATH = self._key_path
        arca_auth.CERT_PATH = self._cert_path
        arca_auth.TA_FILES_PATH = self._ta_path
        arca_auth.PROD = self.is_production
        arca_auth.WSDL_WSAA = arca_settings.WSDL_WSAA_PROD if self.is_production else arca_settings.WSDL_WSAA_HOM

        arca_ws.CUIT = self.cuit

    def _ensure_settings(self):
        """Re-aplica settings antes de cada operación (por si otra instancia los cambió)."""
        self._configure_settings()

    @property
    def wsfe(self) -> ArcaWebService:
        """Obtiene o crea la instancia de WSFE (Factura Electrónica)."""
        if self._wsfe is None:
            wsdl = WSDL_FEV1_PROD if self.is_production else WSDL_FEV1_HOM
            self._wsfe = self._create_webservice_with_ta_fallback(
                wsdl=wsdl,
                service='wsfe',
                error_prefix='Error al conectar con WSFE',
            )
        return self._wsfe

    @property
    def ws_constancia(self) -> ArcaWebService:
        """Obtiene o crea la instancia del servicio de Constancia de Inscripción (padrón)."""
        if self._ws_constancia is None:
            wsdl = WSDL_CONSTANCIA_PROD if self.is_production else WSDL_CONSTANCIA_HOM
            self._ws_constancia = self._create_webservice_with_ta_fallback(
                wsdl=wsdl,
                service='ws_sr_constancia_inscripcion',
                error_prefix='Error al conectar con servicio de padrón',
            )
        return self._ws_constancia

    def _create_webservice_with_ta_fallback(self, wsdl: str, service: str, error_prefix: str) -> ArcaWebService:
        """Crea webservice reutilizando TA local válido cuando existe.

        Serializa la inicialización por servicio para evitar carreras entre
        procesos que intenten renovar TA al mismo tiempo.
        """
        with self._ta_file_lock(service):
            self._ensure_settings()

            for attempt in range(3):
                try:
                    return ArcaWebService(wsdl, service, enable_logging=False)
                except Exception as e:
                    message = str(e)
                    lowered = self._normalize_wsaa_message(message)

                    if 'ya posee un ta valido' in lowered and attempt < 2:
                        # Otro proceso puede haber emitido TA válido recién.
                        # Reintentar reutilizando cache local.
                        time.sleep(attempt + 1)
                        self._ensure_settings()
                        if self._has_valid_local_ta(service):
                            continue
                        continue

                    raise ArcaAuthError(f'{error_prefix}: {message}')

        raise ArcaAuthError(f'{error_prefix}: no se pudo inicializar el servicio')

    @contextmanager
    def _ta_file_lock(self, service: str):
        lock_path = os.path.join(self._ta_path, f'{service}.lock')
        lock_file = open(lock_path, 'a+')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    def _has_valid_local_ta(self, service: str) -> bool:
        ta_file = os.path.join(self._ta_path, f'{service}.pkl')
        if not os.path.exists(ta_file):
            return False

        try:
            with open(ta_file, 'rb') as f:
                ticket = pickle.load(f)
        except (OSError, pickle.UnpicklingError, EOFError, AttributeError, ValueError):
            return False

        is_expired = getattr(ticket, 'is_expired', None)
        if isinstance(is_expired, bool):
            return not is_expired

        expires = getattr(ticket, 'expires', None)
        if isinstance(expires, (int, float)):
            return time.time() < float(expires)

        expires_str = getattr(ticket, 'expires_str', None)
        if expires_str:
            # Si no podemos validar con seguridad, dejamos que ArcaWebService decida.
            return True

        return False
    def _normalize_wsaa_message(self, message: str) -> str:
        return (
            (message or '')
            .lower()
            .replace('á', 'a')
            .replace('é', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u')
        )

    def __del__(self):
        """Limpia archivos temporales al destruir el objeto."""
        try:
            for path in [self._cert_path, self._key_path]:
                if os.path.exists(path):
                    os.unlink(path)
            # Limpiar tokens temporales
            if os.path.exists(self._temp_dir):
                for f in os.listdir(self._temp_dir):
                    os.unlink(os.path.join(self._temp_dir, f))
                os.rmdir(self._temp_dir)
        except Exception:
            pass

    def fe_comp_ultimo_autorizado(self, punto_venta: int, tipo_cbte: int) -> int:
        """
        Obtiene el último número de comprobante autorizado.

        Args:
            punto_venta: Punto de venta
            tipo_cbte: Tipo de comprobante (1=FC A, 6=FC B, etc.)

        Returns:
            Último número de comprobante autorizado
        """
        try:
            self._ensure_settings()
            ws = self.wsfe

            auth = ws.get_type('FEAuthRequest')
            auth['Token'] = ws.token
            auth['Sign'] = ws.sign
            auth['Cuit'] = ws.cuit

            data = {
                'Auth': auth,
                'PtoVta': punto_venta,
                'CbteTipo': tipo_cbte,
            }

            request_started = time.perf_counter()
            self._log_ws_request('FECompUltimoAutorizado', 'wsfe', data)
            result = ws.send_request('FECompUltimoAutorizado', data)
            self._log_ws_response(
                'FECompUltimoAutorizado',
                'wsfe',
                result,
                'raw',
                duration_ms=(time.perf_counter() - request_started) * 1000,
            )
            return result.CbteNro
        except ArcaError:
            raise
        except Exception as e:
            raise ArcaError(f'Error al consultar último comprobante: {str(e)}')

    def fe_cae_solicitar(self, request_data: dict) -> dict:
        """
        Solicita CAE para un comprobante.

        Args:
            request_data: Datos del comprobante con estructura:
                {
                    'FeCAEReq': {
                        'FeCabReq': { 'CantReg': 1, 'PtoVta': 1, 'CbteTipo': 1 },
                        'FeDetReq': { 'FECAEDetRequest': { ... } }
                    }
                }

        Returns:
            Respuesta parseada con CAE, vencimiento y resultado
        """
        try:
            self._ensure_settings()
            ws = self.wsfe

            auth = ws.get_type('FEAuthRequest')
            auth['Token'] = ws.token
            auth['Sign'] = ws.sign
            auth['Cuit'] = ws.cuit

            # FeDetReq espera un dict, no una lista
            fe_cae_req = request_data['FeCAEReq']
            det_req = fe_cae_req['FeDetReq']['FECAEDetRequest']

            # Si viene como lista, tomar el primer elemento
            if isinstance(det_req, list):
                det_req = det_req[0]

            data = {
                'Auth': auth,
                'FeCAEReq': {
                    'FeCabReq': fe_cae_req['FeCabReq'],
                    'FeDetReq': {
                        'FECAEDetRequest': det_req
                    }
                }
            }

            request_started = time.perf_counter()
            self._log_ws_request('FECAESolicitar', 'wsfe', data)

            result = ws.send_request('FECAESolicitar', data)
            self._log_ws_response(
                'FECAESolicitar',
                'wsfe',
                result,
                'raw',
                duration_ms=(time.perf_counter() - request_started) * 1000,
            )

            parsed_response = self._parse_cae_response(result)
            self._log_ws_response('FECAESolicitar', 'wsfe', parsed_response, 'parsed')
            return parsed_response
        except ArcaError:
            raise
        except Exception as e:
            raise ArcaError(f'Error al solicitar CAE: {str(e)}')

    def fe_comp_consultar(self, tipo_cbte: int, punto_venta: int, numero: int) -> dict:
        """
        Consulta un comprobante ya emitido.

        Args:
            tipo_cbte: Tipo de comprobante
            punto_venta: Punto de venta
            numero: Número de comprobante

        Returns:
            Datos del comprobante consultado
        """
        try:
            self._ensure_settings()
            ws = self.wsfe

            auth = ws.get_type('FEAuthRequest')
            auth['Token'] = ws.token
            auth['Sign'] = ws.sign
            auth['Cuit'] = ws.cuit

            data = {
                'Auth': auth,
                'FeCompConsReq': {
                    'CbteTipo': tipo_cbte,
                    'CbteNro': numero,
                    'PtoVta': punto_venta,
                }
            }

            request_started = time.perf_counter()
            self._log_ws_request('FECompConsultar', 'wsfe', data)
            result = ws.send_request('FECompConsultar', data)
            self._log_ws_response(
                'FECompConsultar',
                'wsfe',
                result,
                'raw',
                duration_ms=(time.perf_counter() - request_started) * 1000,
            )

            if hasattr(result, 'ResultGet') and result.ResultGet:
                cbte = result.ResultGet
                return {
                    'encontrado': True,
                    'tipo_cbte': cbte.CbteTipo,
                    'punto_venta': cbte.PtoVta,
                    'cbte_desde': cbte.CbteDesde,
                    'cbte_hasta': cbte.CbteHasta,
                    'concepto': cbte.Concepto,
                    'doc_tipo': cbte.DocTipo,
                    'doc_nro': cbte.DocNro,
                    'fecha_cbte': str(cbte.CbteFch) if cbte.CbteFch else None,
                    'imp_total': cbte.ImpTotal,
                    'imp_neto': cbte.ImpNeto,
                    'imp_iva': cbte.ImpIVA,
                    'imp_trib': cbte.ImpTrib,
                    'imp_op_ex': cbte.ImpOpEx,
                    'imp_tot_conc': getattr(cbte, 'ImpTotConc', 0),
                    'mon_id': getattr(cbte, 'MonId', 'PES'),
                    'mon_cotiz': getattr(cbte, 'MonCotiz', 1),
                    'cae': str(cbte.CodAutorizacion) if cbte.CodAutorizacion else None,
                    'cae_vto': str(cbte.FchVto) if getattr(cbte, 'FchVto', None) else None,
                    'resultado': cbte.Resultado,
                }

            return {'encontrado': False}

        except ArcaError:
            raise
        except Exception as e:
            raise ArcaError(f'Error al consultar comprobante: {str(e)}')

    def consultar_padron(self, cuit_consulta: str) -> dict:
        """
        Consulta el padrón de ARCA para obtener datos de un contribuyente.

        Args:
            cuit_consulta: CUIT a consultar (sin guiones)

        Returns:
            Datos del contribuyente
        """
        try:
            self._ensure_settings()
            ws = self.ws_constancia

            cuit_int = int(cuit_consulta.replace('-', ''))
            if hasattr(ws, 'get_persona'):
                result = ws.get_persona(cuit_int)
            else:
                data = {
                    'token': ws.token,
                    'sign': ws.sign,
                    'cuitRepresentada': ws.cuit,
                    'idPersona': cuit_int,
                }
                result = ws.send_request('getPersona_v2', data)

            if hasattr(result, 'personaReturn') and result.personaReturn:
                persona = result.personaReturn
                nombre = getattr(persona, 'nombre', '') or ''
                apellido = getattr(persona, 'apellido', '') or ''

                if apellido and nombre:
                    razon_social = f'{apellido}, {nombre}'
                elif nombre:
                    razon_social = nombre
                else:
                    razon_social = getattr(persona, 'razonSocial', '') or str(cuit_consulta)

                direccion = None
                if hasattr(persona, 'domicilio') and persona.domicilio:
                    dom = persona.domicilio[0] if isinstance(persona.domicilio, list) else persona.domicilio
                    direccion = self._format_domicilio(dom)

                condicion_iva = None
                if hasattr(persona, 'datosGenerales') and persona.datosGenerales:
                    dg = persona.datosGenerales
                    if hasattr(dg, 'idPersona'):
                        pass
                    # Intentar obtener categoría impositiva
                    if hasattr(persona, 'datosRegimenGeneral') and persona.datosRegimenGeneral:
                        condicion_iva = 'IVA Responsable Inscripto'
                    elif hasattr(persona, 'datosMonotributo') and persona.datosMonotributo:
                        condicion_iva = 'Responsable Monotributo'

                return {
                    'success': True,
                    'data': {
                        'cuit': cuit_consulta.replace('-', ''),
                        'razon_social': razon_social,
                        'direccion': direccion,
                        'condicion_iva': condicion_iva,
                    }
                }

            return {'success': False, 'error': 'Persona no encontrada'}

        except ArcaError:
            raise
        except Exception as e:
            raise ArcaError(f'Error al consultar padrón: {str(e)}')

    def _parse_cae_response(self, result) -> dict:
        """Parsea la respuesta de FECAESolicitar."""
        response = {
            'resultado': None,
            'reproceso': None,
            'cae': None,
            'cae_vencimiento': None,
            'numero_comprobante': None,
            'observaciones': [],
            'errores': [],
        }

        if hasattr(result, 'FeCabResp') and result.FeCabResp:
            response['resultado'] = result.FeCabResp.Resultado
            response['reproceso'] = getattr(result.FeCabResp, 'Reproceso', None)

        if hasattr(result, 'FeDetResp') and result.FeDetResp:
            det_list = result.FeDetResp.FECAEDetResponse
            if det_list:
                det = det_list[0] if isinstance(det_list, list) else det_list
                response['cae'] = str(det.CAE) if det.CAE else None
                response['cae_vencimiento'] = str(det.CAEFchVto) if det.CAEFchVto else None
                response['numero_comprobante'] = det.CbteDesde
                response['resultado'] = det.Resultado

                if hasattr(det, 'Observaciones') and det.Observaciones:
                    obs_list = det.Observaciones.Obs if hasattr(det.Observaciones, 'Obs') else det.Observaciones
                    if obs_list:
                        if not isinstance(obs_list, list):
                            obs_list = [obs_list]
                        response['observaciones'] = [
                            {'code': getattr(obs, 'Code', None), 'msg': getattr(obs, 'Msg', '')}
                            for obs in obs_list
                        ]

        if hasattr(result, 'Errors') and result.Errors:
            err_list = result.Errors.Err if hasattr(result.Errors, 'Err') else result.Errors
            if err_list:
                if not isinstance(err_list, list):
                    err_list = [err_list]
                response['errores'] = [
                    {'code': getattr(err, 'Code', None), 'msg': getattr(err, 'Msg', '')}
                    for err in err_list
                ]

        return response

    def _log_ws_request(self, method_name: str, wsid: str, params: dict):
        if not self.verbose_logs:
            return

        self._emit_verbose_log({
            'event': 'arca.ws.request',
            'environment': self.environment,
            'arca_ambiente': self.ambiente,
            'method': method_name,
            'wsid': wsid,
            'params': self._sanitize_payload(params),
        })

    def _log_ws_response(self, method_name: str, wsid: str, response, stage: str, duration_ms: float | None = None):
        if not self.verbose_logs:
            return

        if stage == 'raw' and not self.verbose_include_raw:
            return

        payload = {
            'event': 'arca.ws.response',
            'environment': self.environment,
            'arca_ambiente': self.ambiente,
            'method': method_name,
            'wsid': wsid,
            'stage': stage,
            'response': self._to_json_safe(response),
        }

        if duration_ms is not None:
            payload['duration_ms'] = round(float(duration_ms), 2)

        self._emit_verbose_log(payload)

    def _emit_verbose_log(self, payload: dict):
        try:
            json_payload = self._format_json(payload)
            logger.info('ARCA_VERBOSE %s', json_payload)
        except Exception:
            logger.info('ARCA_VERBOSE %s', str(payload))

    def _format_json(self, payload: dict) -> str:
        safe_payload = self._to_json_safe(payload)
        if self.verbose_format == 'pretty':
            return json.dumps(safe_payload, ensure_ascii=False, indent=2)
        return json.dumps(safe_payload, ensure_ascii=False, separators=(',', ':'))

    def _sanitize_payload(self, value):
        secret_keys = {'token', 'sign'}

        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                key_str = str(key)
                if key_str.lower() in secret_keys:
                    continue
                sanitized[key_str] = self._sanitize_payload(item)
            return sanitized

        if isinstance(value, list):
            return [self._sanitize_payload(item) for item in value]

        if isinstance(value, tuple):
            return [self._sanitize_payload(item) for item in value]

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                try:
                    parsed = ast.literal_eval(stripped)
                    return self._sanitize_payload(parsed)
                except Exception:
                    pass
            return self._redact_secret_fragments(value)

        converted = self._to_json_safe(value)
        if isinstance(converted, dict):
            return self._sanitize_payload(converted)
        if isinstance(converted, list):
            return [self._sanitize_payload(item) for item in converted]
        if isinstance(converted, str):
            return self._redact_secret_fragments(converted)
        return converted

    def _to_json_safe(self, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, dict):
            return {str(k): self._to_json_safe(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._to_json_safe(v) for v in value]

        try:
            zeep_helpers = importlib.import_module('zeep.helpers')
            serialize_object = getattr(zeep_helpers, 'serialize_object', None)
            if serialize_object is None:
                raise AttributeError('serialize_object no disponible')

            serialized = serialize_object(value)
            if serialized is not value:
                return self._to_json_safe(serialized)
        except Exception:
            pass

        if hasattr(value, '__dict__'):
            serialized = {}
            for key, attr in vars(value).items():
                if str(key).startswith('_'):
                    continue
                serialized[str(key)] = self._to_json_safe(attr)
            if serialized:
                return serialized

        return str(value)

    def _redact_secret_fragments(self, value: str) -> str:
        redacted = re.sub(r"(['\"]?Token['\"]?\s*:\s*['\"])([^'\"]*)(['\"])", r"\1***\3", value)
        redacted = re.sub(r"(['\"]?Sign['\"]?\s*:\s*['\"])([^'\"]*)(['\"])", r"\1***\3", redacted)
        return redacted

    def _format_domicilio(self, domicilio) -> Optional[str]:
        """Formatea el domicilio de ARCA."""
        parts = []
        for attr in ['direccion', 'localidad', 'descripcionProvincia']:
            val = getattr(domicilio, attr, None)
            if val:
                parts.append(str(val))
        return ', '.join(parts) if parts else None
