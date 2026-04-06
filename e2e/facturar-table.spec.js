import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Facturar — Table Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/facturar')
    await page.waitForTimeout(1500)
  })

  // ── Page loads with lote selector ────────────────────────────────────

  test('page loads with lote selector visible', async ({ page }) => {
    const loteSelect = page.locator('select').filter({ hasText: /Seleccionar lote/ })
    await expect(loteSelect).toBeVisible({ timeout: 10_000 })

    // Should have at least the placeholder option
    const options = loteSelect.locator('option')
    const count = await options.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  // ── Select a lote → table populates ──────────────────────────────────

  test('select a lote populates facturas table', async ({ page }) => {
    const loteSelect = page.locator('select').filter({ hasText: /Seleccionar lote/ })
    await expect(loteSelect).toBeVisible({ timeout: 10_000 })

    // Select the first real lote (second option after placeholder)
    const options = loteSelect.locator('option')
    const optionCount = await options.count()
    expect(optionCount).toBeGreaterThan(1)

    const firstLoteValue = await options.nth(1).getAttribute('value')
    await loteSelect.selectOption(firstLoteValue)

    // Table should show at least one row or the "No hay facturas" message
    const tableBody = page.locator('tbody')
    await expect(tableBody).toBeVisible({ timeout: 10_000 })

    // Column headers should be visible
    for (const header of ['Receptor', 'Tipo', 'Fecha', 'Importe', 'Estado', 'Acciones']) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
  })

  // ── Ver button opens ItemsModal ──────────────────────────────────────

  test('Ver button opens ItemsModal with factura detail', async ({ page }) => {
    const loteSelect = page.locator('select').filter({ hasText: /Seleccionar lote/ })
    await expect(loteSelect).toBeVisible({ timeout: 10_000 })

    // Select first lote
    const firstLoteValue = await loteSelect.locator('option').nth(1).getAttribute('value')
    await loteSelect.selectOption(firstLoteValue)

    // Wait for table rows
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })

    // Click the Ver (eye icon) button in the last column
    const verButton = page.locator('tbody tr').first().locator('td:last-child button').first()
    await verButton.click()

    // ItemsModal should open with title "Detalle de Factura"
    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Detalle de Factura/ })
    await expect(modal).toBeVisible({ timeout: 10_000 })
  })

  // ── ItemsModal shows item fields ─────────────────────────────────────

  test('ItemsModal shows factura detail fields', async ({ page }) => {
    const loteSelect = page.locator('select').filter({ hasText: /Seleccionar lote/ })
    await expect(loteSelect).toBeVisible({ timeout: 10_000 })

    // Select first lote
    const firstLoteValue = await loteSelect.locator('option').nth(1).getAttribute('value')
    await loteSelect.selectOption(firstLoteValue)

    // Wait for rows and click Ver (eye icon in last column)
    const firstRow = page.locator('tbody tr').first()
    await expect(firstRow).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(500)
    await firstRow.locator('td:last-child button').first().click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Detalle de Factura/ })
    await expect(modal).toBeVisible({ timeout: 15_000 })

    // Factura detail fields should be visible inside modal
    await expect(modal.getByText(/Receptor/)).toBeVisible({ timeout: 10_000 })
    await expect(modal.getByText(/Tipo comprobante/i)).toBeVisible()
    await expect(modal.getByText(/Fecha emisión/i)).toBeVisible()
    await expect(modal.getByText(/Importe total/i)).toBeVisible()
  })

  // ── Buttons area shows Importar CSV and Facturar ─────────────────────

  test('action buttons Importar CSV and Facturar are visible', async ({ page }) => {
    await expect(
      page.getByRole('button', { name: /Importar CSV/i })
    ).toBeVisible({ timeout: 10_000 })

    await expect(
      page.getByRole('button', { name: /Facturar/i })
    ).toBeVisible({ timeout: 10_000 })
  })
})
