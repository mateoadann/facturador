<div align="center">
  <img src="factura.png" alt="Facturador" width="120" height="120" />
  <h1>Facturador</h1>
</div>


Sistema de facturacion electronica masiva para Argentina, integrado con ARCA (ex-AFIP).

## Stack

- **Backend**: Flask 3, SQLAlchemy 2, Celery, Redis, PostgreSQL 16
- **Frontend**: React 18, Vite, TanStack Query, Zustand, Tailwind CSS
- **Integracion ARCA**: modulo independiente en `arca_integration/`

## Estado del proyecto (2026-02-10)

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

- Email: `admin@facturador.local`
- Password: `admin123`

## Estructura del proyecto

```text
.
├── backend/           # API Flask + Celery
├── frontend/          # SPA React
├── arca_integration/  # Integracion ARCA desacoplada
├── factura.png        # Logo base del proyecto
├── frontend/public/favicon.png # Favicon con fondo blanco
├── docker-compose.yml
└── Makefile
```

Para mas detalle de arquitectura y flujos, ver `CLAUDE.md`.
