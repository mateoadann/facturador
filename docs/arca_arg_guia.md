# Guía de uso: librería arca_arg

Librería Python para conectar con los servicios web SOAP de ARCA (ex-AFIP) de Argentina.

**Repositorio:** GitHub (MIT License)
**Instalación:** `pip install arca_arg`

---

## Índice

1. [Requisitos previos](#requisitos-previos)
2. [Configuración inicial](#configuración-inicial)
3. [Conceptos clave](#conceptos-clave)
4. [Factura Electrónica (WSFE)](#factura-electrónica-wsfe)
5. [Consulta de Padrón](#consulta-de-padrón)
6. [Referencia de tipos WSFE](#referencia-de-tipos-wsfe)
7. [Servicios disponibles](#servicios-disponibles)
8. [Troubleshooting](#troubleshooting)

---

## Requisitos previos

### 1. Generar clave privada

```bash
openssl genrsa -out mi_clave.key 2048
```

### 2. Generar CSR (Certificate Signing Request)

```bash
openssl req -new -key mi_clave.key \
  -subj "/C=AR/O=Mi Empresa SRL/CN=mi_certificado/serialNumber=CUIT 20123456789" \
  -out mi_clave.csr
```

### 3. Obtener certificado en ARCA

1. Ingresar al portal de ARCA con CUIT y clave fiscal
2. Ir a **"Administración de Certificados Digitales"**
3. Para homologación: **"WSASS - Autogestión Certificados Homologación"**
4. Subir el archivo `.csr` generado
5. Descargar el certificado `.crt` o `.pem` resultante

### 4. Autorizar servicio web

En el portal de ARCA, autorizar el servicio web que necesitás usar (ej: `wsfe` para facturación electrónica).

---

## Configuración inicial

La librería usa configuración global a través del módulo `arca_arg.settings`:

```python
import arca_arg.settings as config

# Rutas a los archivos de certificado y clave
config.PRIVATE_KEY_PATH = '/ruta/a/mi_clave.key'
config.CERT_PATH = '/ruta/a/mi_certificado.pem'

# Directorio donde se guardarán los tokens de acceso (TA)
config.TA_FILES_PATH = '/ruta/a/tokens/'

# CUIT del contribuyente (sin guiones)
config.CUIT = '20123456789'

# False = homologación (testing), True = producción
config.PROD = False
```

> **Importante:** La configuración es global. Si manejás múltiples CUITs en una misma aplicación, debés re-configurar los settings antes de cada operación.

---

## Conceptos clave

### ArcaWebService

Es la clase principal. Crea una conexión a un servicio SOAP específico de ARCA.

```python
from arca_arg.webservice import ArcaWebService
from arca_arg.settings import WSDL_FEV1_HOM

# Crear instancia del servicio WSFE (Factura Electrónica) en homologación
ws = ArcaWebService(WSDL_FEV1_HOM, 'wsfe')
```

Parámetros:
- **wsdl**: URL del WSDL del servicio. La librería exporta constantes para cada servicio.
- **service_name**: Nombre del servicio web según ARCA.
- **enable_logging** (opcional): `True` para ver los XML SOAP en consola.

### Propiedades de la instancia

Una vez creada la instancia, tiene disponibles:

```python
ws.token   # Token de autenticación (se obtiene automáticamente)
ws.sign    # Firma de autenticación (se obtiene automáticamente)
ws.cuit    # CUIT configurado en settings
```

### Métodos principales

| Método | Descripción |
|--------|-------------|
| `ws.list_methods()` | Lista todas las operaciones disponibles del servicio |
| `ws.method_help('NombreMetodo')` | Muestra firma y parámetros de un método |
| `ws.get_type('NombreTipo')` | Obtiene la estructura de un tipo complejo SOAP |
| `ws.send_request('NombreMetodo', data)` | Envía una request al servicio |

---

## Factura Electrónica (WSFE)

### Crear instancia

```python
from arca_arg.webservice import ArcaWebService
from arca_arg.settings import WSDL_FEV1_HOM, WSDL_FEV1_PROD
import arca_arg.settings as config

# Configurar settings primero
config.PRIVATE_KEY_PATH = '/ruta/a/key.key'
config.CERT_PATH = '/ruta/a/cert.pem'
config.TA_FILES_PATH = '/ruta/a/tokens/'
config.CUIT = '20123456789'
config.PROD = False

# Crear servicio
wsfe = ArcaWebService(WSDL_FEV1_HOM, 'wsfe')
```

### Explorar métodos disponibles

```python
# Ver todos los métodos del servicio
wsfe.list_methods()
# Resultado: ['FECAESolicitar', 'FECompUltimoAutorizado', 'FECompConsultar', ...]

# Ver detalle de un método
wsfe.method_help('FECAESolicitar')

# Ver estructura de un tipo
wsfe.get_type('FECAECabRequest')
# Resultado: {'CantReg': None, 'PtoVta': None, 'CbteTipo': None}
```

### Consultar último comprobante autorizado

```python
# Construir Auth
auth = wsfe.get_type('FEAuthRequest')
auth['Token'] = wsfe.token
auth['Sign'] = wsfe.sign
auth['Cuit'] = wsfe.cuit

# Consultar
data = {
    'Auth': auth,
    'PtoVta': 1,         # Punto de venta
    'CbteTipo': 1,       # 1 = Factura A
}

result = wsfe.send_request('FECompUltimoAutorizado', data)
print(f'Último autorizado: {result.CbteNro}')
print(f'Próximo número: {result.CbteNro + 1}')
```

### Emitir una factura (FECAESolicitar)

Este es el flujo completo para emitir una Factura A con IVA 21%:

```python
# 1. Construir Auth
auth = wsfe.get_type('FEAuthRequest')
auth['Token'] = wsfe.token
auth['Sign'] = wsfe.sign
auth['Cuit'] = wsfe.cuit

# 2. Cabecera del comprobante
cab_req = wsfe.get_type('FECAECabRequest')
cab_req['CantReg'] = 1       # Cantidad de comprobantes en el lote
cab_req['PtoVta'] = 1        # Punto de venta
cab_req['CbteTipo'] = 1      # 1 = Factura A

# 3. Detalle del comprobante
det_request = {
    'Concepto': 1,                # 1=Productos, 2=Servicios, 3=Ambos
    'DocTipo': 80,                # 80=CUIT, 96=DNI, 99=Otro
    'DocNro': 27293188217,        # Número de documento del receptor
    'CbteDesde': 6,               # Número de comprobante desde
    'CbteHasta': 6,               # Número de comprobante hasta (mismo para 1 factura)
    'CbteFch': '20250124',        # Fecha de emisión YYYYMMDD
    'ImpTotal': 121,              # Importe total
    'ImpTotConc': 0,              # Importe neto no gravado
    'ImpNeto': 100,               # Importe neto gravado
    'ImpOpEx': 0,                 # Importe operaciones exentas
    'ImpIVA': 21,                 # Importe total de IVA
    'ImpTrib': 0,                 # Importe total de tributos
    'MonId': 'PES',               # Moneda (PES=Pesos, DOL=Dólares, 060=Euros)
    'MonCotiz': 1,                # Cotización de la moneda
    'Iva': {                      # Detalle de alícuotas IVA
        'AlicIva': {
            'Id': 5,              # 5=21%, 4=10.5%, 6=27%, 3=0%, 8=5%, 9=2.5%
            'BaseImp': 100,       # Base imponible
            'Importe': 21         # Importe de IVA
        }
    }
}

# 4. Armar el request completo
data = {
    'Auth': auth,
    'FeCAEReq': {
        'FeCabReq': cab_req,
        'FeDetReq': {
            'FECAEDetRequest': det_request
        }
    }
}

# 5. Enviar
result = wsfe.send_request('FECAESolicitar', data)

# 6. Leer respuesta
print(f'Resultado: {result.FeCabResp.Resultado}')  # 'A' = Aprobado, 'R' = Rechazado

if result.FeDetResp:
    det = result.FeDetResp.FECAEDetResponse[0]
    print(f'CAE: {det.CAE}')
    print(f'Vencimiento CAE: {det.CAEFchVto}')
    print(f'Comprobante N°: {det.CbteDesde}')

    # Observaciones (pueden existir incluso si fue aprobado)
    if det.Observaciones:
        for obs in det.Observaciones.Obs:
            print(f'Observación [{obs.Code}]: {obs.Msg}')

# Errores globales
if result.Errors:
    for err in result.Errors.Err:
        print(f'Error [{err.Code}]: {err.Msg}')
```

### Factura de Servicios (Concepto 2)

Para servicios se requieren campos adicionales de fechas:

```python
det_request = {
    'Concepto': 2,                # 2 = Servicios
    'DocTipo': 80,
    'DocNro': 27293188217,
    'CbteDesde': 7,
    'CbteHasta': 7,
    'CbteFch': '20250201',
    'ImpTotal': 12100,
    'ImpTotConc': 0,
    'ImpNeto': 10000,
    'ImpOpEx': 0,
    'ImpIVA': 2100,
    'ImpTrib': 0,
    'MonId': 'PES',
    'MonCotiz': 1,
    # --- Campos obligatorios para servicios ---
    'FchServDesde': '20250101',   # Fecha inicio del servicio
    'FchServHasta': '20250131',   # Fecha fin del servicio
    'FchVtoPago': '20250215',     # Fecha vencimiento de pago
    # ---
    'Iva': {
        'AlicIva': {
            'Id': 5,
            'BaseImp': 10000,
            'Importe': 2100
        }
    }
}
```

### Nota de Crédito con Comprobante Asociado

```python
det_request = {
    'Concepto': 1,
    'DocTipo': 80,
    'DocNro': 27293188217,
    'CbteDesde': 1,
    'CbteHasta': 1,
    'CbteFch': '20250201',
    'ImpTotal': 121,
    'ImpTotConc': 0,
    'ImpNeto': 100,
    'ImpOpEx': 0,
    'ImpIVA': 21,
    'ImpTrib': 0,
    'MonId': 'PES',
    'MonCotiz': 1,
    'Iva': {
        'AlicIva': {
            'Id': 5,
            'BaseImp': 100,
            'Importe': 21
        }
    },
    # Comprobante asociado (la factura original que se está anulando)
    'CbtesAsoc': {
        'CbteAsoc': {
            'Tipo': 1,       # Tipo del comprobante original (1=FC A)
            'PtoVta': 1,     # PV del comprobante original
            'Nro': 6,        # Número del comprobante original
        }
    }
}

# CbteTipo en la cabecera debe ser NC:
cab_req['CbteTipo'] = 3   # 3 = Nota de Crédito A
```

### Factura B (Consumidor Final)

```python
# Cabecera
cab_req['CbteTipo'] = 6   # 6 = Factura B

# Detalle - para consumidor final no se discrimina IVA
det_request = {
    'Concepto': 1,
    'DocTipo': 99,            # 99 = Consumidor Final (sin identificar)
    'DocNro': 0,              # 0 para consumidor final
    'CbteDesde': 1,
    'CbteHasta': 1,
    'CbteFch': '20250201',
    'ImpTotal': 1210,         # Total con IVA incluido
    'ImpTotConc': 0,
    'ImpNeto': 1210,          # En FC B, el neto es igual al total
    'ImpOpEx': 0,
    'ImpIVA': 0,              # En FC B no se discrimina IVA
    'ImpTrib': 0,
    'MonId': 'PES',
    'MonCotiz': 1,
}
```

### Consultar un comprobante emitido

```python
auth = wsfe.get_type('FEAuthRequest')
auth['Token'] = wsfe.token
auth['Sign'] = wsfe.sign
auth['Cuit'] = wsfe.cuit

data = {
    'Auth': auth,
    'FeCompConsReq': {
        'CbteTipo': 1,       # Tipo de comprobante
        'CbteNro': 6,        # Número a consultar
        'PtoVta': 1,         # Punto de venta
    }
}

result = wsfe.send_request('FECompConsultar', data)

if result.ResultGet:
    cbte = result.ResultGet
    print(f'Comprobante: {cbte.CbteTipo}-{cbte.PtoVta}-{cbte.CbteDesde}')
    print(f'Fecha: {cbte.CbteFch}')
    print(f'Total: ${cbte.ImpTotal}')
    print(f'CAE: {cbte.CodAutorizacion}')
    print(f'Resultado: {cbte.Resultado}')
```

---

## Consulta de Padrón

Permite consultar datos de un contribuyente por CUIT.

```python
from arca_arg.webservice import ArcaWebService
from arca_arg.settings import WSDL_CONSTANCIA_HOM

# Crear servicio de constancia de inscripción
ws_padron = ArcaWebService(WSDL_CONSTANCIA_HOM, 'ws_sr_constancia_inscripcion')

# Consultar persona
data = {
    'token': ws_padron.token,
    'sign': ws_padron.sign,
    'cuitRepresentada': ws_padron.cuit,
    'idPersona': 20224107030,       # CUIT a consultar (como entero)
}

result = ws_padron.send_request('getPersona_v2', data)

# Leer datos
if result.personaReturn:
    persona = result.personaReturn
    print(f'Nombre: {persona.nombre}')
    print(f'Apellido: {persona.apellido}')

    if persona.domicilio:
        dom = persona.domicilio[0]
        print(f'Dirección: {dom.direccion}')
        print(f'Localidad: {dom.localidad}')
```

> **Nota:** El servicio de padrón usa `token`/`sign`/`cuitRepresentada` como parámetros directos (en minúscula), a diferencia de WSFE que usa un objeto `Auth` con `Token`/`Sign`/`Cuit`.

---

## Referencia de tipos WSFE

### Tipos de Comprobante (CbteTipo)

| Código | Descripción |
|--------|-------------|
| 1 | Factura A |
| 2 | Nota de Débito A |
| 3 | Nota de Crédito A |
| 6 | Factura B |
| 7 | Nota de Débito B |
| 8 | Nota de Crédito B |
| 11 | Factura C |
| 12 | Nota de Débito C |
| 13 | Nota de Crédito C |
| 51 | Factura M |
| 52 | Nota de Débito M |
| 53 | Nota de Crédito M |

### Tipos de Concepto

| Código | Descripción |
|--------|-------------|
| 1 | Productos |
| 2 | Servicios |
| 3 | Productos y Servicios |

### Tipos de Documento (DocTipo)

| Código | Descripción |
|--------|-------------|
| 80 | CUIT |
| 86 | CUIL |
| 96 | DNI |
| 99 | Doc. (Otro) / Consumidor Final |
| 0 | CI Policía Federal |

### Alícuotas de IVA (Id en AlicIva)

| Código | Alícuota |
|--------|----------|
| 3 | 0% |
| 4 | 10.5% |
| 5 | 21% |
| 6 | 27% |
| 8 | 5% |
| 9 | 2.5% |

### Monedas (MonId)

| Código | Moneda |
|--------|--------|
| PES | Pesos Argentinos |
| DOL | Dólar Estadounidense |
| 060 | Euro |

### Formato de fechas

Todas las fechas en ARCA usan formato **YYYYMMDD** como string:
- `'20250124'` = 24 de enero de 2025

---

## Servicios disponibles

La librería soporta todos los servicios web de ARCA:

| Servicio | Descripción | WSDL Constante |
|----------|-------------|----------------|
| `wsfe` | Factura Electrónica (FEv1) | `WSDL_FEV1_HOM` / `WSDL_FEV1_PROD` |
| `ws_sr_constancia_inscripcion` | Constancia de Inscripción (Padrón) | `WSDL_CONSTANCIA_HOM` / `WSDL_CONSTANCIA_PROD` |
| `wsfex` | Factura de Exportación | - |
| `wsfecred` | Factura de Crédito Electrónica | - |
| `ws_sr_padron_a10` | Padrón Alcance 10 | - |
| `ws_sr_padron_a13` | Padrón Alcance 13 | - |
| `wslpg` | Liquidación Primaria de Granos | - |
| `wscpe` | Carta de Porte Electrónica | - |

Para usar cualquier servicio, el patrón es el mismo:

```python
ws = ArcaWebService(WSDL_URL, 'nombre_servicio')
ws.list_methods()         # Ver operaciones disponibles
ws.method_help('Metodo')  # Ver parámetros
result = ws.send_request('Metodo', data)
```

---

## Troubleshooting

### "Error de autenticación"

- Verificá que el certificado y la clave correspondan entre sí
- Verificá que el servicio web esté autorizado en el portal de ARCA
- Para homologación, usá "WSASS - Autogestión Certificados Homologación"

### "El servicio devuelve error 600"

- Error 600 suele indicar que el CUIT no está autorizado para el servicio
- Verificá la autorización en el portal de ARCA

### "Comprobante rechazado"

- Verificá que el número de comprobante sea el siguiente al último autorizado
- Verificá que las fechas estén en formato YYYYMMDD
- Para servicios (Concepto 2 o 3), son obligatorias: `FchServDesde`, `FchServHasta`, `FchVtoPago`
- El `ImpTotal` debe ser igual a `ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc`

### Tokens de acceso (TA)

La librería cachea automáticamente los tokens en `TA_FILES_PATH`. Si tenés problemas de autenticación, probá borrando los archivos de esa carpeta para forzar una re-autenticación.

### Logging

Para ver las requests/responses SOAP completas:

```python
ws = ArcaWebService(WSDL_FEV1_HOM, 'wsfe', enable_logging=True)
```
