import ssl
import time
import urllib.request
from urllib.error import URLError

from flask import Blueprint, jsonify

from ..utils.decorators import tenant_required

arca_status_bp = Blueprint('arca_status', __name__)

SERVICES = [
    {'name': 'Autenticación', 'key': 'wsaa', 'url': 'https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL'},
    {'name': 'Factura Electrónica', 'key': 'wsfe', 'url': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL'},
    {'name': 'Padrón', 'key': 'padron', 'url': 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL'},
]

# Module-level cache
_cache = {
    'result': None,
    'timestamp': 0,
}
CACHE_TTL = 60  # seconds


def _create_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers('DEFAULT@SECLEVEL=1')
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _check_service(url, ctx):
    try:
        response = urllib.request.urlopen(url, context=ctx, timeout=5)
        if response.status < 500:
            return 'operational'
        return 'degraded'
    except URLError as e:
        # Check if it's an HTTP error with a status code
        if hasattr(e, 'code') and e.code >= 500:
            return 'degraded'
        return 'down'
    except Exception:
        return 'down'


def _get_status():
    now = time.time()
    if _cache['result'] and (now - _cache['timestamp']) < CACHE_TTL:
        return _cache['result']

    ctx = _create_ssl_context()
    services = []
    for svc in SERVICES:
        status = _check_service(svc['url'], ctx)
        services.append({
            'name': svc['name'],
            'key': svc['key'],
            'status': status,
        })

    statuses = {s['key']: s['status'] for s in services}

    # Determine overall status
    if all(s['status'] == 'operational' for s in services):
        overall = 'operational'
    elif statuses.get('wsfe') == 'down' or statuses.get('wsaa') == 'down':
        overall = 'down'
    else:
        overall = 'degraded'

    result = {
        'overall': overall,
        'services': services,
    }

    _cache['result'] = result
    _cache['timestamp'] = now

    return result


@arca_status_bp.route('/status', methods=['GET'])
@tenant_required
def get_arca_status():
    result = _get_status()
    return jsonify(result)
