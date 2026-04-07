# SSL DH_KEY_TOO_SMALL — Fix para AFIP/ARCA con OpenSSL 3.x

## El problema

Al conectar desde el VPS de producción (Ubuntu 24.04, Python 3.11-slim, OpenSSL 3.5.5) a los servidores de AFIP/ARCA, la conexión TLS falla con:

```
SSLError(SSLError(1, '[SSL: DH_KEY_TOO_SMALL] dh key too small (_ssl.c:1016)'))
```

**Root cause**: AFIP usa parámetros Diffie-Hellman de 1024 bits en `servicios1.afip.gov.ar` (WSFE). OpenSSL 3.x exige mínimo 2048 bits por defecto (SECLEVEL=2).

**Nota**: No todos los servicios de AFIP tienen este problema. WSAA (`wsaa.afip.gov.ar`) funciona bien. Solo WSFE producción (`servicios1.afip.gov.ar`) usa DH keys pequeños.

## Solución que funciona

Parchear `ssl.SSLContext.wrap_socket` para forzar `SECLEVEL=1` en TODA conexión TLS, justo antes del handshake.

**Archivo**: `arca_integration/client.py` (al inicio, antes de importar `arca_arg`)

```python
import ssl

_orig_wrap_socket = ssl.SSLContext.wrap_socket

def _patched_wrap_socket(self, *args, **kwargs):
    try:
        self.set_ciphers('DEFAULT@SECLEVEL=1')
    except Exception:
        pass
    return _orig_wrap_socket(self, *args, **kwargs)

ssl.SSLContext.wrap_socket = _patched_wrap_socket
```

**Por qué funciona**: `wrap_socket` es el último método llamado antes de que se establezca la conexión TLS. Parchearlo garantiza que SECLEVEL=1 se aplica sin importar cómo se creó el SSLContext (urllib3, requests, zeep, etc.).

## Approaches que NO funcionaron

### 1. Parchear `ssl.SSLContext.__init__`
```python
_orig = ssl.SSLContext.__init__
def _patched(self, *args, **kwargs):
    _orig(self, *args, **kwargs)
    self.set_ciphers('DEFAULT@SECLEVEL=1')
ssl.SSLContext.__init__ = _patched
```
**Error**: `object.__init__() takes exactly one argument` — SSLContext es una clase C de bajo nivel, su `__init__` no se puede parchear de forma segura.

### 2. Parchear `ssl.create_default_context`
```python
_orig = ssl.create_default_context
def _patched(*args, **kwargs):
    ctx = _orig(*args, **kwargs)
    ctx.set_ciphers('DEFAULT@SECLEVEL=1')
    return ctx
ssl.create_default_context = _patched
```
**Por qué falla**: urllib3/requests NO usa `ssl.create_default_context()` para crear su SSLContext. Crea `ssl.SSLContext()` directamente, así que el patch nunca se ejecuta.

### 3. Variable de entorno `OPENSSL_CONF`
```dockerfile
# En docker-compose.prod.yml
environment:
  - OPENSSL_CONF=/app/arca_integration/openssl_afip.cnf
```
Con archivo `openssl_afip.cnf`:
```ini
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
CipherString = DEFAULT:@SECLEVEL=1
```
**Por qué falla**: OpenSSL 3.5.5 con Python 3.11 ignora `OPENSSL_CONF` para la configuración de SSL contexts. La variable se lee pero no afecta los ciphers de los contexts creados por Python.

### 4. Modificar `/etc/ssl/openssl.cnf` en el Dockerfile
```dockerfile
RUN python patch_openssl.py  # Agrega ssl_sect al config del sistema
```
**Por qué falla**: Mismo problema que #3. OpenSSL 3.5.5 no aplica las secciones `ssl_conf` del config file a los SSLContext creados por Python. El config se lee pero solo afecta operaciones de línea de comandos (`openssl s_client`), no la librería.

## Cómo verificar

Desde dentro del container de producción:
```bash
docker exec facturador_api python -c "
import ssl, urllib.request
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.set_ciphers('DEFAULT@SECLEVEL=1')
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.urlopen('https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL', context=ctx, timeout=15)
print('WSFE:', req.status)
"
```
Debe imprimir `WSFE: 200`.

## Contexto técnico

- **VPS**: AWS us-east-1, Ubuntu 24.04
- **Container**: `python:3.11-slim` con OpenSSL 3.5.5
- **Servidor AFIP afectado**: `servicios1.afip.gov.ar:443` (WSFE producción)
- **Cipher negociado**: `DHE-RSA-AES256-GCM-SHA384` (TLSv1.2)
- **Stack**: Flask + Gunicorn → arca_arg → zeep → requests → urllib3 → ssl
- **El fix aplica a**: container `facturador_api` y `facturador_worker`

## Referencia

- PR #42-47: intentos fallidos
- PR #50-51: fix definitivo (`wrap_socket`)
- AFIP status page: `https://status.afipsdk.com`
