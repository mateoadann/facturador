# AGENTS.md
Guide for agentic coding tools working in this repository.

## Rule files status
- No `.cursor/rules/` directory was found.
- No `.cursorrules` file was found.
- No `.github/copilot-instructions.md` file was found.
- If any of these files appear later, treat them as highest-priority local instructions.

## Project overview
- Stack: Flask + SQLAlchemy + Celery backend, React + Vite frontend, ARCA integration module.
- Backend path: `backend/`
- Frontend path: `frontend/`
- ARCA module path: `arca_integration/`
- App is multi-tenant: tenant isolation is mandatory in data access.

## Build, run, lint, test commands

### Root shortcuts (Makefile)
- `make up` -> start full docker stack.
- `make up-build` -> start stack with image rebuild.
- `make migrate` -> run DB migrations.
- `make seed` -> seed tenant + admin.
- `make bootstrap` -> up + migrate + seed.
- `make test-backend` -> run backend tests in container.
- `make lint-frontend` -> run frontend lint in container.

### Docker compose direct
- `docker-compose up -d`
- `docker-compose down`
- `docker-compose build api worker`
- `docker-compose logs -f api`
- `docker-compose logs -f worker`
- `docker-compose logs -f frontend`

### Backend local
- `cd backend && pip install -r requirements.txt`
- `cd backend && python run.py`
- `cd backend && celery -A celery_worker.celery worker --loglevel=info`
- `cd backend && flask db upgrade`
- `cd backend && flask db migrate -m "message"`

### Frontend local
- `cd frontend && npm install`
- `cd frontend && npm run dev`
- `cd frontend && npm run build`
- `cd frontend && npm run lint`

## Test workflows (focus on single test)
- All backend tests: `cd backend && python -m pytest`
- One file: `cd backend && python -m pytest tests/test_facturas.py -v`
- One class: `cd backend && python -m pytest tests/test_facturas.py::TestBulkDeleteFacturas -v`
- One test: `cd backend && python -m pytest tests/test_facturas.py::TestBulkDeleteFacturas::test_bulk_delete -v`
- Filter by keyword: `cd backend && python -m pytest -k "test_login" -v`
- List routes: `docker-compose exec -T api flask routes`
- Syntax check: `python3 -m py_compile backend/app/api/facturas.py`

## Note on pytest
- `pytest` is not pinned in `backend/requirements.txt`.
- If missing locally: `cd backend && pip install pytest`.

## Architecture pointers
- Flask app factory: `backend/app/__init__.py`
- API blueprints: `backend/app/api/*.py`
- Models: `backend/app/models/*.py`
- CSV import path: `POST /api/facturas/import`
- Lote processing task: `backend/app/tasks/facturacion.py`
- ARCA wrappers: `arca_integration/client.py`, `arca_integration/services/*`
- Frontend API client: `frontend/src/api/client.js`
- Main invoicing screen: `frontend/src/pages/facturar/index.jsx`

## Backend style guidelines (Python)
- Follow existing PEP8-like style and 4-space indentation.
- Keep endpoint functions thin; move logic to services/helpers.
- Use clear names and small focused functions.
- Naming conventions:
  - `snake_case` -> functions, vars, modules.
  - `PascalCase` -> classes.
  - `UPPER_SNAKE_CASE` -> constants.
- Imports order:
  1) stdlib
  2) third-party
  3) local imports
- Group imports with blank lines between groups.
- Prefer explicit `Decimal` arithmetic for money and taxes.
- Avoid float calculations for accounting logic.
- Add type hints where they improve readability and safety.
- Prefer explicit return types for new helpers/services.

## API and error handling conventions
- Validate request payloads early and return 4xx on invalid input.
- Return errors as JSON, e.g. `jsonify({'error': '...'}), status_code`.
- Preserve actionable error messages for operators.
- Use broad `except Exception` only when translating external library errors.
- Keep payload key names stable; frontend depends on exact response keys.

## Multi-tenancy and data integrity rules
- Always filter tenant-owned entities by `tenant_id`.
- Use `@tenant_required` for tenant-context routes.
- Use `@admin_required` for admin-only operations.
- Never leak cross-tenant data.
- When deleting/updating related entities, sync aggregate counters.
- Empty lotes should be removed to avoid stale UI and label collisions.

## Frontend style guidelines (React)
- Codebase is JS-only (no TypeScript).
- Follow existing formatting:
  - single quotes
  - no semicolons
  - functional components + hooks
- Naming conventions:
  - `PascalCase` -> components
  - `camelCase` -> vars/functions
- Use `@/` alias for imports from `src`.
- Keep HTTP calls centralized in `frontend/src/api/client.js`.
- Use TanStack Query for server state.
- In mutations, invalidate relevant query keys after success.
- Show user-facing failures with `toast.error(...)`.
- Avoid fragile optimistic assumptions in billing flows.

## CSV and invoicing domain guidance
- CSV parser supports UTF-8 and Latin-1.
- Supported date formats: `YYYY-MM-DD` and `DD/MM/YYYY`.
- Decimal parser accepts dot and comma separators.
- CSV import supports grouped multi-line invoices (multiple item rows).
- Keep lote/facturador/environment consistency within a lote.

## Migration and schema guidelines
- Use Flask-Migrate: `flask db migrate`, `flask db upgrade`.
- Avoid rewriting old migrations unless explicitly required.
- Prefer additive and backward-compatible schema changes.

## Change checklist for agents
- Understand affected backend and frontend flows before editing.
- Add regression tests for bug fixes when feasible.
- Run targeted tests for touched modules.
- Run frontend lint/build when touching frontend logic.
- Verify tenant isolation is still enforced.
- Verify lote counters and lifecycle remain consistent.
- Document non-obvious behavior changes in your final summary.

## Fast file map
- `backend/app/api/facturas.py` -> import, invoice CRUD, bulk delete.
- `backend/app/api/lotes.py` -> lote listing/facturar/delete.
- `backend/app/services/csv_parser.py` -> CSV parsing and grouping.
- `backend/app/tasks/facturacion.py` -> async ARCA emission.
- `backend/app/services/comprobante_renderer.py` -> invoice HTML/QR.
- `backend/app/services/comprobante_pdf.py` -> HTML->PDF rendering.
- `frontend/src/pages/facturar/index.jsx` -> lote picker/table/actions.
- `frontend/src/hooks/useJobStatus.js` -> Celery polling.

Keep changes minimal, tenant-safe, and test-backed.
