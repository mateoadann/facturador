# AGENTS.md
Code review contract for AI reviewers in this repository.

## Priority Of Rule Files
- If `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` exist, treat them as higher priority than this file.

## Project Context
- Stack: Flask + SQLAlchemy + Celery backend, React + Vite frontend, ARCA integration.
- Paths: `backend/`, `frontend/`, `arca_integration/`.
- Domain: multi-tenant invoicing. Tenant isolation is mandatory.

## Critical Rules (All Files)

REJECT if:
- A change can leak data across tenants.
- A write flow skips audit logging when audit should apply.
- Money/tax arithmetic uses float where `Decimal` should be used.
- API response keys are changed without a compatibility reason.
- Errors are swallowed silently or returned with non-actionable messages.
- Security-sensitive behavior is weakened (auth, permissions, rate limiting).

REQUIRE:
- Keep changes minimal, focused, and consistent with existing patterns.
- Preserve backward compatibility unless the task explicitly requires breaking changes.
- Document non-obvious behavior changes in final output.

PREFER:
- Small functions, explicit names, and early validation.

## Backend Rules (Flask/Python)

REJECT if:
- Tenant-owned queries are not filtered by `tenant_id`.
- Resource endpoints miss `@permission_required('recurso:accion')`.
- `@tenant_required` is used where `@permission_required` should be used.
- Write endpoints do not call `log_action()` before commit.
- Broad `except Exception` is used without translating external/library failures.
- Old migrations are rewritten without explicit need.

REQUIRE:
- Keep endpoint functions thin; move business logic to services/helpers.
- Return JSON errors with clear message and status code, e.g. `jsonify({'error': '...'}), 400`.
- Keep imports grouped in order: stdlib, third-party, local.
- Use Flask-Migrate (`flask db migrate`, `flask db upgrade`) for schema changes.

PREFER:
- Type hints on new/changed helpers and explicit return types where they improve clarity.
- `Decimal` for accounting paths.

## Frontend Rules (React/JS)

REJECT if:
- TypeScript is introduced (codebase is JS-only).
- HTTP calls are added outside `frontend/src/api/client.js` without clear reason.
- Mutations do not invalidate relevant TanStack Query keys.
- User-facing failures are not surfaced with `toast.error(...)` where appropriate.
- New protected pages/actions are added without permission gating.

REQUIRE:
- Follow existing style: single quotes, no semicolons, functional components with hooks.
- Use `@/` alias for imports from `src`.
- Keep billing/invoicing UI flows conservative (avoid fragile optimistic assumptions).

## Domain Invariants

REJECT if:
- Lote/facturador/environment consistency is broken within a lote.
- Aggregate counters are not synced after delete/update operations.
- Empty lotes are left behind when they should be removed.

REQUIRE:
- CSV import compatibility for UTF-8 and Latin-1.
- Date parsing compatibility for `YYYY-MM-DD` and `DD/MM/YYYY`.
- Decimal parsing compatibility for dot and comma separators.
- Support grouped multi-line invoices in CSV import flow.

## Testing And Validation Expectations

REQUIRE:
- For backend changes, run targeted pytest for touched modules when feasible.
- For frontend changes, run `npm run lint` and `npm run build` when feasible.
- Verify tenant isolation and permissions on changed paths.

## Branch And Release Governance

REJECT if:
- A change is proposed directly on `main`/`master` without pull request context.
- A stable branch (`main`, `release/*`) is used for exploratory or unrelated changes.
- A release/hotfix change lacks explicit risk notes or validation evidence.

REQUIRE:
- Use branch prefixes: `feature/*`, `fix/*`, `chore/*`, `hotfix/*`.
- Merge into `main` only through pull requests with required checks green.
- Tag stable releases with semantic versioning (`vMAJOR.MINOR.PATCH`).

PREFER:
- Small PRs scoped to one purpose.
- Separate tooling/governance changes from product logic changes.

Useful commands:
- Backend all tests: `cd backend && python -m pytest`
- Backend single file: `cd backend && python -m pytest tests/test_facturas.py -v`
- Backend single test: `cd backend && python -m pytest tests/test_facturas.py::TestBulkDeleteFacturas::test_bulk_delete -v`
- Frontend lint: `cd frontend && npm run lint`
- Frontend build: `cd frontend && npm run build`

## Fast File Map
- `backend/app/api/facturas.py`: import, invoice CRUD, bulk delete.
- `backend/app/api/lotes.py`: lote listing/facturar/delete.
- `backend/app/api/usuarios.py`: user CRUD, activate/deactivate.
- `backend/app/api/audit.py`: audit log listing.
- `backend/app/services/permissions.py`: role and permission definitions.
- `backend/app/services/audit.py`: `log_action()` helper.
- `backend/app/services/csv_parser.py`: CSV parsing and grouping.
- `backend/app/tasks/facturacion.py`: async ARCA emission.
- `backend/app/services/comprobante_renderer.py`: invoice HTML and QR.
- `backend/app/services/comprobante_pdf.py`: HTML to PDF rendering.
- `frontend/src/pages/facturar/index.jsx`: lote picker/table/actions.
- `frontend/src/pages/usuarios/index.jsx`: user management page.
- `frontend/src/pages/auditoria/index.jsx`: audit log viewer.
- `frontend/src/hooks/usePermission.js`: permission hooks.
- `frontend/src/hooks/useJobStatus.js`: Celery polling.

## Response Format (Mandatory)
First line MUST be exactly one of:

`STATUS: PASSED`
`STATUS: FAILED`

If FAILED, report each issue as:
- `path:line - rule - why it fails - suggested fix`
