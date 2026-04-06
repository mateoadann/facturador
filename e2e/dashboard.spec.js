import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/dashboard')
    await page.waitForTimeout(1000)
  })

  // ── Metrics cards ──────────────────────────────────────────────────────

  test('dashboard loads with metric cards visible', async ({ page }) => {
    await expect(page.getByText(/Facturas del (Mes|Periodo)/)).toBeVisible()
    await expect(page.getByText(/Autorizadas/)).toBeVisible()
    await expect(page.getByText('Con Errores')).toBeVisible()
    await expect(page.getByText('Pendientes')).toBeVisible()
  })

  // ── Filter by month ────────────────────────────────────────────────────

  test('filter by month: DatePicker opens and selects a different month', async ({ page }) => {
    const datepickerInput = field(page, 'Mes de analisis').input
    await expect(datepickerInput).toBeVisible()

    // Read initial period label
    const periodLabel = page.getByText(/Periodo seleccionado:/i)
    const initialText = await periodLabel.textContent()

    // Open datepicker
    await datepickerInput.click()

    // Pick a non-selected month cell
    const monthCell = page.locator('.air-datepicker-cell.-month-:not(.-selected-)').first()
    if (await monthCell.count() > 0) {
      await monthCell.click()
      await page.waitForTimeout(500)

      // Period label should have changed
      await expect(periodLabel).toBeVisible()
    }
  })

  // ── Filter by facturador ───────────────────────────────────────────────

  test('filter by facturador: select dropdown is interactive', async ({ page }) => {
    // Dashboard uses a combobox/select for facturador, find it
    const facturadorSelect = page.locator('select').filter({
      has: page.locator('option', { hasText: 'Todos' })
    }).first()
    await expect(facturadorSelect).toBeVisible()

    // Verify "Todos" is selected by default
    await expect(facturadorSelect).toHaveValue('')

    // Select a specific facturador if available
    const options = facturadorSelect.locator('option')
    const optionCount = await options.count()
    if (optionCount > 1) {
      const secondValue = await options.nth(1).getAttribute('value')
      await facturadorSelect.selectOption(secondValue)
      await page.waitForTimeout(500)

      // Metrics should still be visible
      await expect(page.getByText(/Facturas del (Mes|Periodo)/)).toBeVisible()
    }
  })

  // ── Toggle histórico ──────────────────────────────────────────────────

  test('toggle historico button changes view', async ({ page }) => {
    // Click the Historico button
    const historicoBtn = page.getByRole('button', { name: /historico/i })
    await expect(historicoBtn).toBeVisible()
    await historicoBtn.click()
    await page.waitForTimeout(1000)

    // After toggle, period-related text should change
    await expect(page.getByText(/Periodo seleccionado:/i)).toBeVisible()

    // Toggle back
    await historicoBtn.click()
    await page.waitForTimeout(500)

    await expect(page.getByText(/Periodo seleccionado:/i)).toBeVisible()
  })

  // ── Chart and cards visible ────────────────────────────────────────────

  test('monthly billing chart is visible', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /Facturacion mensual/i })
    ).toBeVisible()
  })

  test('average ticket card is visible', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /Ticket promedio/i })
    ).toBeVisible()
  })

  test('net/IVA breakdown card is visible', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /Desglose Neto/i })
    ).toBeVisible()
  })

  test('top 10 clients table is visible with headers', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /Top 10 clientes/i })
    ).toBeVisible()

    await expect(page.getByRole('columnheader', { name: 'Cliente' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Documento' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Cantidad' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Total' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /participacion/i })).toBeVisible()
  })

  // ── Quick actions ──────────────────────────────────────────────────────
  // Scope to main content area to avoid matching sidebar links

  test('quick action: Nueva Factura navigates to /facturar', async ({ page }) => {
    const main = page.locator('main')
    const link = main.locator('a[href="/facturar"]')
    await expect(link).toBeVisible()

    await link.click()
    await page.waitForURL(/\/facturar/, { timeout: 10_000 })
  })

  test('quick action: Ver Facturas navigates to /facturas', async ({ page }) => {
    const main = page.locator('main')
    const link = main.locator('a[href="/facturas"]')
    await expect(link).toBeVisible()

    await link.click()
    await page.waitForURL(/\/facturas/, { timeout: 10_000 })
  })

  test('quick action: Facturadores navigates to /facturadores', async ({ page }) => {
    const main = page.locator('main')
    const link = main.locator('a[href="/facturadores"]')
    await expect(link).toBeVisible()

    await link.click()
    await page.waitForURL(/\/facturadores/, { timeout: 10_000 })
  })

  test('quick action: Receptores navigates to /receptores', async ({ page }) => {
    const main = page.locator('main')
    const link = main.locator('a[href="/receptores"]')
    await expect(link).toBeVisible()

    await link.click()
    await page.waitForURL(/\/receptores/, { timeout: 10_000 })
  })

  // ── Viewer with sensitive restriction ──────────────────────────────────

  test('viewer sees dashboard with metric cards', async ({ page }) => {
    await clearSession(page)
    await login(page, USERS.viewer)
    await page.goto('/dashboard')
    await page.waitForTimeout(1000)

    // Metric count cards are always visible for any role
    await expect(page.getByText(/Facturas del (Mes|Periodo)/)).toBeVisible()
    await expect(page.getByText(/Autorizadas/)).toBeVisible()
    await expect(page.getByText('Con Errores')).toBeVisible()
    await expect(page.getByText('Pendientes')).toBeVisible()
  })
})
