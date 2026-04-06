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

const TEST_CUIT = '20888888880'

function cleanupTestReceptor() {
  dbExec(`DELETE FROM receptor WHERE doc_nro = '${TEST_CUIT}';`)
}

test.describe('Receptores', () => {
  test.beforeAll(() => cleanupTestReceptor())
  test.afterAll(() => cleanupTestReceptor())

  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/receptores')
    await page.waitForTimeout(1000)
  })

  // ── Table loads ────────────────────────────────────────────────────────

  test('table loads with expected columns', async ({ page }) => {
    for (const header of ['CUIT/CUIL', 'Razón Social', 'Condición IVA', 'Email', 'Estado', 'Acciones']) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
    // At least one receptor should be visible (DB has ~10)
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10_000 })
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  // ── Search bar ─────────────────────────────────────────────────────────

  test('search bar filters results by receptor name', async ({ page }) => {
    // Wait for table to load
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })

    // Get total before search
    const totalBefore = await page.locator('tbody tr').count()

    // Get the name of the first receptor to use as search term
    const firstRowName = await page.locator('tbody tr').first().locator('td').nth(1).locator('p.font-medium').textContent()
    const searchTerm = firstRowName.trim().split(' ')[0] // Use first word

    const searchInput = page.locator('input[placeholder*="Buscar"]')
    await searchInput.fill(searchTerm)

    // Wait for the query to re-fetch
    await page.waitForTimeout(1000)

    // Results should contain the search term
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10_000 })
    const filteredCount = await rows.count()
    expect(filteredCount).toBeGreaterThanOrEqual(1)

    // Every visible row should contain the search term
    for (let i = 0; i < filteredCount; i++) {
      const rowText = await rows.nth(i).textContent()
      expect(rowText.toLowerCase()).toContain(searchTerm.toLowerCase())
    }
  })

  // ── Pagination info ────────────────────────────────────────────────────

  test('pagination info shows "Mostrando X de Y receptores"', async ({ page }) => {
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })

    // The page shows "Página X de Y · Mostrando N de M receptores"
    await expect(page.getByText(/Mostrando \d+ de \d+ receptores/).first()).toBeVisible()
  })

  // ── Create: modal opens ────────────────────────────────────────────────

  test('create receptor: modal opens with all fields', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo receptor/i }).click()

    await expect(page.getByRole('heading', { name: /nuevo receptor/i })).toBeVisible()

    // CUIT/CUIL field has a special layout (grid with Buscar button), check via label text
    await expect(page.locator('label', { hasText: 'CUIT/CUIL' })).toBeVisible()
    await expect(field(page, 'Razón Social').input).toBeVisible()
    await expect(field(page, 'Dirección').input).toBeVisible()
    await expect(field(page, 'Condición IVA').select).toBeVisible()
    await expect(field(page, 'Email').input).toBeVisible()
  })

  // ── Create: validation ─────────────────────────────────────────────────

  test('create receptor: validation — submit empty shows error', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo receptor/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo receptor/i })).toBeVisible()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Receptor/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    // Backend returns "Campo doc_nro es requerido" — shown in toast or inline error
    await expect(page.getByText(/es requerido/i).first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Create: happy path ─────────────────────────────────────────────────

  test('create receptor: happy path — fill form and save', async ({ page }) => {
    cleanupTestReceptor()

    await page.getByRole('button', { name: /nuevo receptor/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo receptor/i })).toBeVisible()

    // CUIT/CUIL input is inside a grid layout under the CUIT/CUIL label
    const cuitContainer = page.locator('label', { hasText: 'CUIT/CUIL' }).locator('..')
    await cuitContainer.locator('input').fill(TEST_CUIT)

    await field(page, 'Razón Social').input.fill('E2E Test Receptor')
    await field(page, 'Dirección').input.fill('Calle Test 789')
    await field(page, 'Condición IVA').select.selectOption('IVA Responsable Inscripto')
    await field(page, 'Email').input.fill('e2e-receptor@test.com')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Receptor/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Receptor creado correctamente/i).first()).toBeVisible({ timeout: 10_000 })

    // Verify appears in table
    await expect(page.getByText('E2E Test Receptor')).toBeVisible({ timeout: 5_000 })
  })

  // ── Edit receptor ──────────────────────────────────────────────────────

  test('edit receptor: modal pre-filled and saves changes', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Receptor' })
    await expect(row).toBeVisible({ timeout: 10_000 })
    await row.locator('button[title="Editar"]').click()

    await expect(page.getByRole('heading', { name: /editar receptor/i })).toBeVisible()

    // Razón Social should be pre-filled
    await expect(field(page, 'Razón Social').input).toHaveValue('E2E Test Receptor')

    // Change dirección
    await field(page, 'Dirección').input.clear()
    await field(page, 'Dirección').input.fill('Calle Editada 101')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Editar Receptor/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Receptor actualizado correctamente/i).first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Deactivate receptor ────────────────────────────────────────────────

  test('deactivate receptor: badge changes to Inactivo', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Receptor' })
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Accept the confirm dialog
    page.on('dialog', (dialog) => dialog.accept())

    await row.locator('button[title="Desactivar"]').click()

    await expect(page.getByText(/Receptor desactivado/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(row.getByText('Inactivo')).toBeVisible()
  })

  // ── Search clears on input clear ───────────────────────────────────────

  test('search clears on input clear — all results return', async ({ page }) => {
    // Wait for table to load
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })

    // Get the "Mostrando X of Y" text to know total
    const paginationText = await page.getByText(/Mostrando \d+ de \d+ receptores/).first().textContent()
    const totalMatch = paginationText.match(/de (\d+) receptores/)
    const totalBefore = totalMatch ? parseInt(totalMatch[1], 10) : 0

    // Type a search term
    const searchInput = page.locator('input[placeholder*="Buscar"]')
    await searchInput.fill('zzzznotfound')
    await page.waitForTimeout(1000)

    // Should show no results or fewer results
    const noResults = page.getByText('No se encontraron receptores')
    await expect(noResults).toBeVisible({ timeout: 5_000 })

    // Clear the search
    await searchInput.clear()
    await page.waitForTimeout(1000)

    // All results should return
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })
    const paginationAfter = await page.getByText(/Mostrando \d+ de \d+ receptores/).first().textContent()
    const totalAfterMatch = paginationAfter.match(/de (\d+) receptores/)
    const totalAfter = totalAfterMatch ? parseInt(totalAfterMatch[1], 10) : 0

    expect(totalAfter).toBe(totalBefore)
  })
})
