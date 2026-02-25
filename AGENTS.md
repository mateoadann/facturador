# AGENTS.md

Guidelines for coding agents working in this repository.

## 1) Rule Priority And External Instructions

- If present, treat these as higher-priority than this file:
  - `.cursor/rules/**`
  - `.cursorrules`
  - `.github/copilot-instructions.md`
- Current repository check: none of the files above were found.

## 2) Project Snapshot

- Product: multi-tenant electronic invoicing for Argentina (ARCA/ex-AFIP).
- Backend: Flask + SQLAlchemy + Celery.
- Frontend: React (JS only) + Vite + TanStack Query + Zustand.
- Integration: `arca_integration/` module (separate Flask package style).
- Key folders:
  - `backend/`
  - `frontend/`
  - `arca_integration/`

## 3) Core Invariants (Do Not Break)

- Tenant isolation is mandatory on tenant-owned data (`tenant_id` scoping).
- Writes that change business state should be audited with `log_action(...)`.
- Accounting and tax math must use `Decimal` (not float) for internal logic.
- Permission checks must remain explicit and consistent.
- API responses should remain backward compatible unless explicitly changed.

## 4) Environment And Workflow

- Prefer Docker/Make targets over host-level Python/Node commands.
- Default environment is dev compose stack (`docker-compose.yml` + `docker-compose.dev.yml`).
- Use small focused changes; avoid broad refactors unless requested.

## 5) Build, Lint, Test Commands

### Full-stack / lifecycle

- Start stack: `make up`
- Start with rebuild: `make up-build`
- Stop stack: `make down`
- Service status: `make ps`

### Backend checks

- Backend tests (default): `make test-backend`
- Alias default suite: `make test`

#### Run a single backend test file

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api sh -lc "cd /app && python -m pytest tests/test_lotes.py -v"`

#### Run a single backend test case

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api sh -lc "cd /app && python -m pytest tests/test_lotes.py::TestFacturarLote::test_facturar_lote_retries_error_facturas_by_resetting_to_pending -v"`

#### Run backend tests by keyword

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api sh -lc "cd /app && python -m pytest -k 'login or permisos' -v"`

### Frontend checks

- Lint: `make lint-frontend`
- Build: `make build-frontend`

#### Lint one frontend file

- `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm run lint -- src/pages/facturas/index.jsx`

### Pre-push gate

- `make pre-push` (backend tests + frontend lint + frontend build)

## 6) Database / Migrations

- Apply migrations: `make migrate`
- Create migration: `make makemigrations m="descripcion"`
- Seed initial data: `make seed`
- Do not rewrite old migrations unless explicitly requested.

## 7) Backend Coding Style (Flask/Python)

### Imports and formatting

- Import order: stdlib, third-party, local.
- Keep modules focused; avoid large endpoint files when adding new behavior.
- Follow existing project style; avoid introducing new formatting conventions.

### API and endpoint patterns

- Use `@permission_required('recurso:accion')` on protected endpoints.
- Keep endpoint handlers thin; move non-trivial logic to helpers/services/tasks.
- Return JSON error payloads as `{'error': '...'}` with appropriate HTTP codes.
- Preserve established response keys unless change is intentional and coordinated.

### Tenant safety and queries

- Scope tenant-owned queries with `tenant_id`.
- Scope updates/deletes as strictly as reads.
- For async tasks, pass `tenant_id` into task args when needed for safe querying.

### Error handling

- Avoid broad `except Exception` in business flows.
- Catch expected exceptions per layer (validation, SMTP/network, ARCA integration).
- Return actionable, stable error messages/codes.
- Never silently swallow failures (`pass` in except blocks is disallowed).

### Money, tax, and invariants

- Use `Decimal` for calculation/comparison/rounding.
- Convert to float only at strict external API boundaries if required.
- Keep lote counters (`total_facturas`, `facturas_ok`, `facturas_error`) synchronized with DB state.

### Auditing

- Call `log_action(...)` for meaningful write actions prior to commit.
- Read endpoints should not perform hidden writes.

## 8) Frontend Coding Style (React/JS)

- JavaScript only (no TypeScript introduction).
- Use functional components and hooks.
- Use `@/` alias for imports from `frontend/src`.
- Keep HTTP calls centralized in `frontend/src/api/client.js`.
- Reuse existing UI primitives in `frontend/src/components/ui`.

### State, data fetching, and UX behavior

- Use TanStack Query for server state.
- After mutations, invalidate relevant query keys.
- Surface user-facing failures with `toast.error(...)` where appropriate.
- Keep permission-gated actions behind `usePermission(...)` / permission checks.

### Naming conventions

- Components: PascalCase (`BulkEmailModal.jsx`).
- Hooks: camelCase prefixed with `use` (`useJobStatus.js`).
- Files should follow local folder conventions and stay consistent.

## 9) Domain-Specific Guidance

- Lote consistency matters: keep facturador/environment coherence per lote.
- CSV import must preserve compatibility expectations:
  - UTF-8 and Latin-1 decoding
  - dates `YYYY-MM-DD` and `DD/MM/YYYY`
  - decimal separators dot/comma
  - grouped multi-line invoice rows
- Email send rules must respect invoice status and recipient email presence.

## 10) Quick File Map

- `backend/app/api/facturas.py` - CSV import, factura CRUD, comprobantes, bulk delete.
- `backend/app/api/lotes.py` - lote listing, facturar, delete, bulk email endpoints.
- `backend/app/tasks/facturacion.py` - async ARCA authorization flow.
- `backend/app/tasks/email.py` - async email send (single and lote batch).
- `frontend/src/api/client.js` - centralized API client methods.
