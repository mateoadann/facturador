import { test, expect } from '@playwright/test'
import { execFileSync } from 'child_process'
import { USERS, field, login } from './helpers.js'

const CWD = '/Users/mateo/Documents/clientes/facturador/facturador_v2'
const DC = ['compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.dev.yml']

function dbExec(sql) {
  try {
    execFileSync('docker', [
      ...DC, 'exec', '-T', 'postgres',
      'psql', '-U', 'facturador', '-d', 'facturador', '-c', sql,
    ], { cwd: CWD })
  } catch { /* non-critical */ }
}

const TEST_CUIT = '20999999990'

function cleanupTestFacturador() {
  dbExec(`DELETE FROM facturador WHERE cuit = '${TEST_CUIT}';`)
}

test.describe('Facturadores', () => {
  test.beforeAll(() => cleanupTestFacturador())
  test.afterAll(() => cleanupTestFacturador())

  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/facturadores')
    await page.waitForTimeout(1000)
  })

  // ── Table ──────────────────────────────────────────────────────────────

  test('table loads with expected columns', async ({ page }) => {
    for (const header of ['CUIT', 'Razón Social', 'Punto de Venta', 'Ambiente', 'Certificados', 'Estado', 'Acciones']) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
    await expect(page.getByText('Mateo Adan')).toBeVisible()
    await expect(page.getByText('Bavera y Asoc')).toBeVisible()
  })

  // ── Create: modal opens ────────────────────────────────────────────────

  test('create facturador: modal opens with all fields', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo facturador/i }).click()

    await expect(page.getByRole('heading', { name: /nuevo facturador/i })).toBeVisible()

    await expect(field(page, 'CUIT').input).toBeVisible()
    await expect(field(page, 'Razón Social').input).toBeVisible()
    await expect(field(page, 'Dirección').input).toBeVisible()
    await expect(field(page, 'Condición IVA').select).toBeVisible()
    await expect(field(page, 'Punto de Venta').input).toBeVisible()
    await expect(field(page, 'Ingresos Brutos').input).toBeVisible()
    await expect(field(page, 'Fecha de Inicio de Actividades').input).toBeVisible()
  })

  // ── Create: validation ─────────────────────────────────────────────────

  test('create facturador: validation — submit empty shows error', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo facturador/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo facturador/i })).toBeVisible()

    // Find Guardar inside modal (avoid ambiguity)
    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Facturador/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    // Error shows in toast + modal — use .first()
    await expect(page.getByText(/es requerido/i).first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Create: happy path ─────────────────────────────────────────────────

  test('create facturador: happy path — fill form and save', async ({ page }) => {
    cleanupTestFacturador()

    await page.getByRole('button', { name: /nuevo facturador/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo facturador/i })).toBeVisible()

    await field(page, 'CUIT').input.fill(TEST_CUIT)
    await field(page, 'Razón Social').input.fill('E2E Test Facturador')
    await field(page, 'Dirección').input.fill('Calle Test 123')
    await field(page, 'Condición IVA').select.selectOption('IVA Responsable Inscripto')
    await field(page, 'Punto de Venta').input.fill('99')
    await field(page, 'Ingresos Brutos').input.fill('901-999999-0')

    // Fecha de Inicio: AirDatepicker is readOnly, click to open and pick a date
    const fechaInput = field(page, 'Fecha de Inicio de Actividades').input
    await fechaInput.click()
    // Pick first available day cell in the calendar popup
    await page.locator('.air-datepicker-cell.-day-').first().click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Facturador/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Facturador creado correctamente/i).first()).toBeVisible({ timeout: 10_000 })

    // Verify appears in table
    await expect(page.getByText('E2E Test Facturador')).toBeVisible({ timeout: 5_000 })
  })

  // ── Edit facturador ────────────────────────────────────────────────────

  test('edit facturador: modal pre-filled and saves changes', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Facturador' })
    await expect(row).toBeVisible({ timeout: 10_000 })
    await row.locator('button[title="Editar"]').click()

    await expect(page.getByRole('heading', { name: /editar facturador/i })).toBeVisible()

    // CUIT should be disabled in edit mode
    await expect(field(page, 'CUIT').input).toBeDisabled()

    // Razón Social pre-filled
    await expect(field(page, 'Razón Social').input).toHaveValue('E2E Test Facturador')

    // Change dirección
    await field(page, 'Dirección').input.clear()
    await field(page, 'Dirección').input.fill('Calle Editada 456')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Editar Facturador/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Facturador actualizado correctamente/i).first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Deactivate facturador ──────────────────────────────────────────────

  test('deactivate facturador: badge changes to Inactivo', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Facturador' })
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Accept the confirm dialog
    page.on('dialog', (dialog) => dialog.accept())

    await row.locator('button[title="Desactivar"]').click()

    await expect(page.getByText(/Facturador desactivado/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(row.getByText('Inactivo')).toBeVisible()
  })

  // ── Activate facturador ────────────────────────────────────────────────

  test('activate facturador: badge changes to Activo', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Facturador' })
    await expect(row).toBeVisible({ timeout: 10_000 })

    await row.locator('button[title="Activar"]').click()

    await expect(page.getByText(/Facturador activado/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(row.getByText('Activo')).toBeVisible()
  })

  // ── Test connection button ─────────────────────────────────────────────

  test('test connection button is enabled for facturadores with certs', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'Mateo Adan' })
    await expect(row).toBeVisible({ timeout: 10_000 })

    const testBtn = row.locator('button[title="Probar conexión"]')
    await expect(testBtn).toBeVisible()
    await expect(testBtn).toBeEnabled()
  })

  // ── Certificates badge ─────────────────────────────────────────────────

  test('certificates badge: shows Cargados for facturadores with certs', async ({ page }) => {
    const mateoRow = page.locator('tr', { hasText: 'Mateo Adan' })
    await expect(mateoRow.getByText('Cargados')).toBeVisible()

    const baveraRow = page.locator('tr', { hasText: 'Bavera y Asoc' })
    await expect(baveraRow.getByText('Cargados')).toBeVisible()
  })
})
