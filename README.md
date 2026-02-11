<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/factura_dark_mode.png" />
    <source media="(prefers-color-scheme: light)" srcset="frontend/public/factura_light_mode.png" />
    <img src="frontend/public/factura_light_mode.png" alt="Facturador" width="120" height="120" />
  </picture>
  <h1>Facturador</h1>
</div>


Sistema de facturacion electronica masiva para Argentina, integrado con ARCA (ex-AFIP).

## Stack

- **Backend**: Flask 3, SQLAlchemy 2, Celery, Redis, PostgreSQL 16
- **Frontend**: React 18, Vite, TanStack Query, Zustand, Tailwind CSS
- **Integracion ARCA**: libreria `arca_arg` + modulo wrapper en `arca_integration/`

## Referencia libreria ARCA

Este proyecto utiliza la libreria `arca_arg` para interactuar con los web services de ARCA. La integracion se encapsula en `arca_integration/client.py` mediante la clase `ArcaClient`.

- <a href="https://relopezbriega.github.io/blog/2025/01/27/libreria-arca-arg-conectando-tu-aplicacion-con-los-servicios-web-de-arca-afip-con-python/" target="_blank">
    <img alt="Blog arca_arg" src="https://img.shields.io/badge/Blog-arca_arg%20%7C%20Guia%20completa-1f2937?style=flat-square&labelColor=334155&logo=readme&logoColor=white" />
  </a>
- <a href="https://github.com/relopezbriega/arca_arg" target="_blank">
    <img alt="Repositorio GitHub arca_arg" src="https://img.shields.io/badge/GitHub-arca__arg-111827?style=flat-square&labelColor=374151&logo=github&logoColor=white" />
  </a>

## Estado del proyecto (2026-02-11)

Actualmente el proyecto puede:

- Gestionar autenticacion con JWT (login, refresh, contexto de tenant).
- Administrar facturadores (CRUD, activacion/desactivacion, carga de certificados).
- Administrar receptores y consultar padron ARCA por CUIT.
- Importar facturas desde CSV con soporte para:
  - UTF-8 y Latin-1
  - fechas `YYYY-MM-DD` y `DD/MM/YYYY`
  - decimales con punto o coma
  - factura con multiples lineas/items agrupadas en un mismo comprobante
- Trabajar por lotes de facturacion (pendiente/procesando/completado).
- Eliminar facturas en bloque y sincronizar lotes automaticamente:
  - si un lote queda vacio, se elimina
  - la etiqueta de lote vuelve a quedar disponible para reutilizar
- Seleccionar el facturador al momento de facturar un lote (solo activos y con certificados).
- Procesar facturacion masiva en background con Celery y progreso consultable desde frontend.
- Consultar comprobantes en ARCA y obtener ultimo autorizado.
- Generar comprobante HTML y PDF desde backend.
  - motor PDF actual: Playwright + Chromium
  - QR fiscal orientado a validacion en ARCA desde celular
- Seguridad y control de acceso:
  - 3 roles con permisos granulares: admin (todo), operator (operar), viewer (solo lectura)
  - CRUD de usuarios con activacion/desactivacion
  - Proteccion de endpoints por permisos (`@permission_required`)
  - Sidebar dinamica que muestra solo secciones permitidas
  - Rutas protegidas en frontend con redireccion automatica
  - Rate limiting en login: lockout de 15 min tras 5 intentos fallidos
  - Auditoria completa: quien hizo que, cuando, desde que IP, con pagina para admins
  - Cambio de contrasena desde la UI

## Proximas implementaciones

- Documentacion de API con OpenAPI/Swagger (`/docs`).
- Ampliar CI de GitHub Actions (cache optimizada, matriz de versiones y reportes de tests).
- Mejoras en observabilidad (logs estructurados y trazabilidad por lote/factura).
- Mejoras UX en pantallas de facturacion masiva (feedback de errores y reintentos).
- Endurecimiento de reglas de validacion CSV y mensajes de error mas guiados.
- Cobertura de tests de regresion para escenarios criticos de negocio.

## Setup rapido

### Docker (recomendado)

```bash
cp .env.example .env
make up
make migrate
make seed
```

Servicios:

- API: `http://localhost:5003`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Sin Docker

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
python seed.py
python run.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Worker

```bash
cd backend
celery -A celery_worker.celery worker --loglevel=info
```

## Credenciales de desarrollo

Despues de ejecutar `python seed.py`:

| Email | Password | Rol |
|---|---|---|
| `admin@facturador.local` | `admin123` | Admin (acceso total) |
| `operador@facturador.local` | `operador123` | Operador (facturar, receptores) |
| `viewer@facturador.local` | `viewer123` | Viewer (solo lectura) |

## Estructura del proyecto

```text
.
├── backend/           # API Flask + Celery
├── frontend/          # SPA React
├── arca_integration/  # Integracion ARCA desacoplada
├── frontend/public/factura_dark_mode.png  # Logo para fondo oscuro
├── frontend/public/factura_light_mode.png # Logo para fondo claro
├── frontend/public/favicon.png # Favicon
├── docker-compose.yml
└── Makefile
```

Para mas detalle de arquitectura y flujos, ver `CLAUDE.md`.
