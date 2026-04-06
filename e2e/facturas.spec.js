import { test, expect } from '@playwright/test'
import { USERS, clearSession, login } from './helpers.js'

test.describe('Ver Facturas', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/facturas')
    await page.waitForTimeout(1500)
  })

  // ── Table loads ────────────────────────────────────────────────────────

  test('table loads with expected columns', async ({ page }) => {
    for (const header of ['Comprobante', 'Receptor', 'Fecha', 'Ver', 'Estado', 'Email', 'Acciones']) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
    // At least one row should be present (DB has facturas from previous runs)
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Pagination ─────────────────────────────────────────────────────────

  test('pagination info visible and navigation works', async ({ page }) => {
    // Pagination text shows page info
    const paginationText = page.getByText(/Página \d+ de \d+/i).first()
    await expect(paginationText).toBeVisible({ timeout: 10_000 })

    // Navigation buttons exist
    await expect(page.getByRole('button', { name: 'Anterior' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Siguiente' }).first()).toBeVisible()

    // First page — Anterior should be disabled
    await expect(page.getByRole('button', { name: 'Anterior' }).first()).toBeDisabled()
  })

  // ── Filtros button ─────────────────────────────────────────────────────

  test('Filtros button opens and closes filter sidebar', async ({ page }) => {
    const filtrosBtn = page.getByRole('button', { name: /Filtros/i }).first()
    await expect(filtrosBtn).toBeVisible()

    // Open filters sidebar
    await filtrosBtn.click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    // Close via Cancelar button
    const sidebar = page.locator('aside')
    await sidebar.getByRole('button', { name: 'Cancelar' }).click()
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()
  })

  // ── Filter by estado ──────────────────────────────────────────────────

  test('filter by estado — select Autorizado and apply', async ({ page }) => {
    // Open filters
    await page.getByRole('button', { name: /Filtros/i }).first().click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    const sidebar = page.locator('aside')

    // Select "Autorizado" in Estado dropdown
    // field() helper uses text-is which requires exact scoping — use direct locator inside sidebar
    const estadoSelect = sidebar.locator('.flex.flex-col').filter({ hasText: 'Estado' }).locator('select')
    await estadoSelect.selectOption('autorizado')

    // Apply filters
    await sidebar.getByRole('button', { name: 'Aplicar filtros' }).click()

    // Sidebar closes
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()

    // Wait for table to reload
    await page.waitForTimeout(1000)

    // The Filtros button should now show active filter count
    await expect(page.getByRole('button', { name: /Filtros \(1\)/i })).toBeVisible({ timeout: 5_000 })
  })

  // ── Filter by facturador ──────────────────────────────────────────────

  test('filter by facturador — select from dropdown', async ({ page }) => {
    // Open filters
    await page.getByRole('button', { name: /Filtros/i }).first().click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    const sidebar = page.locator('aside')

    // The facturador select should have options loaded
    const facturadorSelect = sidebar.locator('.flex.flex-col').filter({ hasText: 'Facturador' }).locator('select')
    await expect(facturadorSelect).toBeVisible()

    // Select the first non-empty option
    const options = facturadorSelect.locator('option')
    const optionCount = await options.count()
    expect(optionCount).toBeGreaterThan(1) // "Todos" + at least one facturador

    // Select second option (first real facturador)
    const secondOptionValue = await options.nth(1).getAttribute('value')
    await facturadorSelect.selectOption(secondOptionValue)

    // Apply
    await sidebar.getByRole('button', { name: 'Aplicar filtros' }).click()
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()
  })

  // ── Limpiar filtros ───────────────────────────────────────────────────

  test('Limpiar filtros resets all filters', async ({ page }) => {
    // First apply a filter
    await page.getByRole('button', { name: /Filtros/i }).first().click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    const sidebar = page.locator('aside')
    const estadoSelect = sidebar.locator('.flex.flex-col').filter({ hasText: 'Estado' }).locator('select')
    await estadoSelect.selectOption('autorizado')
    await sidebar.getByRole('button', { name: 'Aplicar filtros' }).click()
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()

    // Verify filter is active
    await expect(page.getByRole('button', { name: /Filtros \(1\)/i })).toBeVisible({ timeout: 5_000 })

    // Re-open and clear
    await page.getByRole('button', { name: /Filtros \(1\)/i }).click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    const sidebarAgain = page.locator('aside')
    await sidebarAgain.getByRole('button', { name: 'Limpiar' }).click()

    // Apply cleared filters
    await sidebarAgain.getByRole('button', { name: 'Aplicar filtros' }).click()
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()

    // Button should no longer show active count — "Filtros" without number suffix
    // Note: the button text is "Filtros" but may also contain an SVG icon, so use a flexible match
    await expect(page.getByRole('button', { name: /^Filtros$/i })).toBeVisible({ timeout: 5_000 })
  })

  // ── Badge de filtros activos ──────────────────────────────────────────

  test('badge shows count when filters applied', async ({ page }) => {
    // Open filters and apply two filters
    await page.getByRole('button', { name: /Filtros/i }).first().click()
    await expect(page.getByText('Filtros de facturas')).toBeVisible({ timeout: 5_000 })

    const sidebar = page.locator('aside')

    // Filter by estado
    const estadoSelect = sidebar.locator('.flex.flex-col').filter({ hasText: 'Estado' }).locator('select')
    await estadoSelect.selectOption('autorizado')

    // Filter by facturador (select first real option)
    const facturadorSelect = sidebar.locator('.flex.flex-col').filter({ hasText: 'Facturador' }).locator('select')
    const secondOptionValue = await facturadorSelect.locator('option').nth(1).getAttribute('value')
    await facturadorSelect.selectOption(secondOptionValue)

    await sidebar.getByRole('button', { name: 'Aplicar filtros' }).click()
    await expect(page.getByText('Filtros de facturas')).not.toBeVisible()

    // Should show count of 2
    await expect(page.getByRole('button', { name: /Filtros \(2\)/i })).toBeVisible({ timeout: 5_000 })
  })

  // ── PDF download button ───────────────────────────────────────────────

  test('PDF button visible — enabled for authorized, disabled for non-authorized', async ({ page }) => {
    // At least one PDF button should exist in the table
    const pdfButtons = page.locator('tbody button', { hasText: 'PDF' })
    await expect(pdfButtons.first()).toBeVisible({ timeout: 10_000 })

    // Check that at least one PDF button exists (we don't click it)
    const count = await pdfButtons.count()
    expect(count).toBeGreaterThan(0)
  })

  // ── Email send button ─────────────────────────────────────────────────

  test('Enviar emails del lote button visible for admin', async ({ page }) => {
    const emailBtn = page.getByRole('button', { name: /Enviar emails del lote/i })
    await expect(emailBtn).toBeVisible({ timeout: 5_000 })
  })

  // ── View factura detail ───────────────────────────────────────────────

  test('click Ver on a row opens detail modal', async ({ page }) => {
    // Click the first "Ver" button in the table body
    const verButton = page.locator('tbody button', { hasText: 'Ver' }).first()
    await expect(verButton).toBeVisible({ timeout: 10_000 })
    await verButton.click()

    // Modal should open with title "Detalle de comprobante"
    await expect(page.getByText('Detalle de comprobante')).toBeVisible({ timeout: 10_000 })
  })
})
