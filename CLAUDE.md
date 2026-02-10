# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Facturador - Sistema de facturación electrónica masiva para Argentina (ARCA/ex-AFIP). Aplicación multi-tenant con backend Flask, frontend React y un módulo independiente de integración con ARCA.

## Comandos

### Backend
```bash
# Instalar dependencias
cd backend && pip install -r requirements.txt

# Iniciar servidor de desarrollo
cd backend && python run.py

# Iniciar worker de Celery
cd backend && celery -A celery_worker.celery worker --loglevel=info

# Crear/migrar base de datos
cd backend && flask db init
cd backend && flask db migrate -m "descripcion"
cd backend && flask db upgrade

# Seed de datos iniciales (tenant + admin)
cd backend && python seed.py
```

### Frontend
```bash
cd frontend && npm install
cd frontend && npm run dev      # Dev server en :5173
cd frontend && npm run build    # Build de producción
cd frontend && npm run lint
```

### Tests
```bash
cd backend && python -m pytest              # Correr todos los tests
cd backend && python -m pytest tests/test_auth.py -v   # Tests específicos
cd backend && python -m pytest -k "test_login"         # Filtrar por nombre
```

Tests disponibles: `test_auth.py`, `test_csv_parser.py`, `test_facturadores.py`, `test_receptores.py`, `test_facturas.py`, `test_lotes.py`, `test_factura_builder.py`. Usan SQLite en memoria (config `TestingConfig`).

### Docker (todos los servicios)
```bash
docker-compose up -d            # PostgreSQL, Redis, API, Worker, Frontend
docker-compose down
```

## Arquitectura

### Backend (Flask)

- **`app/__init__.py`**: Factory pattern con `create_app()`. Registra todos los blueprints bajo `/api/`.
- **`app/extensions.py`**: Instancias globales de SQLAlchemy, JWT, Migrate, Celery. La función `init_celery()` wrappea tareas con el app context de Flask.
- **`app/models/`**: Todos los modelos heredan de `db.Model` y tienen UUIDs como primary keys. Cada modelo tiene `tenant_id` (multi-tenancy por columna). Método `to_dict()` en cada modelo.
- **`app/api/`**: Blueprints REST (auth, dashboard, facturadores, receptores, facturas, lotes, jobs, comprobantes). Todos los endpoints (excepto auth) usan el decorador `@tenant_required` que carga `g.current_user` y `g.tenant_id`.
- **`app/api/comprobantes.py`**: Consultar comprobante existente y último autorizado en ARCA.
- **`app/utils/decorators.py`**: `@tenant_required` verifica JWT + carga tenant. `@admin_required` verifica además rol admin.
- **`app/services/encryption.py`**: Encripta/desencripta certificados con Fernet. Los certs se guardan como `BYTEA` en la tabla `facturador`.
- **`app/services/csv_parser.py`**: Parsea CSV de facturas. Soporta encoding UTF-8 y Latin-1, formatos de fecha YYYY-MM-DD y DD/MM/YYYY, y coma decimal.
- **`app/tasks/facturacion.py`**: Tarea Celery `procesar_lote` que procesa facturas agrupadas por facturador (reutiliza conexión ARCA). Reporta progreso via `self.update_state(state='PROGRESS', meta={current, total, percent})`.

### Frontend (React + Vite)

- **`src/api/client.js`**: Axios con interceptors para JWT. Auto-refresh de token en 401. Objeto `api` exporta todas las funciones agrupadas por recurso.
- **`src/stores/authStore.js`**: Zustand con persistencia. Guarda tokens, user y tenant en localStorage.
- **`src/hooks/useJobStatus.js`**: Hook con TanStack Query que hace polling cada 2s al endpoint `/api/jobs/:taskId/status`. Se detiene automáticamente cuando status es SUCCESS o FAILURE.
- **`src/components/ui/`**: Componentes base (Button, Input, Select, Badge, Card, Modal, Table, Checkbox, Progress, Toast) que replican el design system del archivo `facturador.pen`.
- **`src/components/layout/`**: Layout con Sidebar colapsable + Header. La Sidebar guarda su estado (colapsada/expandida) en Zustand persistido.
- **`src/stores/toastStore.js`**: Sistema de toast notifications. Helpers: `toast.success()`, `toast.error()`, `toast.warning()`, `toast.info()`. Auto-dismiss en 5s.
- **`src/pages/facturar/`**: Flujo principal - seleccionar lote, ver facturas en tabla, importar CSV (ImportModal), confirmar facturación (FacturarModal), ver items (ItemsModal). Progress bar con polling automático.
- **`src/pages/facturadores/`**: CRUD + modal de certificados (`CertificadosModal.jsx`) para upload de .crt/.key.
- **`src/pages/consultar-comprobantes/`**: Consulta de comprobantes en ARCA. Permite buscar por facturador/tipo/PV/número y consultar último autorizado.
- **Alias**: `@/` mapea a `./src/` (configurado en vite.config.js).

### Módulo ARCA (`arca_integration/`)

Módulo independiente de Flask. No importa nada del backend.

- **`client.py`**: Wrapper de `arca_arg`. Recibe cert/key como bytes, crea archivos temporales para la librería y los limpia en `__del__`.
- **`builders/factura_builder.py`**: Pattern Builder para construir requests de ARCA. Convierte fechas a formato YYYYMMDD. Valida campos requeridos y reglas de negocio (servicios requieren fecha_desde/hasta/vto_pago).
- **`services/wsfe.py`**: Servicio de alto nivel para autorizar comprobantes y consultar comprobantes existentes.
- **`constants.py`**: Diccionarios de tipos de comprobante, conceptos, alícuotas IVA, condiciones IVA, monedas.
- **`types.py`**: Dataclasses para tipado: `FacturaRequest`, `CAEResponse`, `Comprobante`, etc.

## Flujo de Facturación Masiva

1. Usuario importa CSV → `POST /api/facturas/import` → crea `Lote` + `Factura`s en estado "pendiente"
2. Usuario revisa tabla → `GET /api/facturas?lote_id=xxx` → puede eliminar facturas
3. Usuario confirma → `POST /api/lotes/:id/facturar` → retorna `{task_id}` → Celery task arranca
4. Frontend polling → `GET /api/jobs/:task_id/status` → `{status: "PROGRESS", progress: {current, total, percent}}`
5. Task completa → actualiza cada factura con CAE o error → actualiza contadores del lote

## Multi-tenancy

Todas las queries DEBEN filtrar por `tenant_id`. El decorador `@tenant_required` carga `g.tenant_id` desde el JWT. Cada tabla relevante tiene `tenant_id` como FK a `tenant`.

## Variables de Entorno

Copiar `.env.example` a `.env`. Variables críticas:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Para Celery broker/backend
- `ENCRYPTION_KEY`: Exactamente 32 caracteres para Fernet (certificados)
- `ARCA_AMBIENTE`: `testing` o `production`

## Design System

Los componentes UI del frontend replican el design system del archivo `facturador.pen`. Colores principales:
- Primary: `#2563EB` (blue-600)
- Success: `#22C55E` / Error: `#EF4444` / Warning: `#F59E0B`
- Backgrounds: card `#FFFFFF`, sidebar `#F8FAFC`, border `#E2E8F0`
- Font: Inter
