import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Auditoria', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/auditoria')
    await page.waitForTimeout(1000)
  })

  // -- Table structure -------------------------------------------------------

  test('table loads with all columns visible', async ({ page }) => {
    await expect(page.getByRole('columnheader', { name: 'Fecha' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Usuario' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Acción' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Recurso' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'IP' })).toBeVisible()
  })

  // -- Audit entries exist ---------------------------------------------------

  test('audit entries exist from previous test actions', async ({ page }) => {
    // Previous E2E tests (login, create facturador, etc.) generate audit entries
    // Verify the empty state message is NOT shown
    await expect(
      page.getByText('No hay registros de auditoria')
    ).not.toBeVisible()

    // At least one row with a Badge (accion column) should be visible
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible()
    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThan(0)
  })

  // -- Filter by accion ------------------------------------------------------

  test('filter by accion text filters results', async ({ page }) => {
    // Type "login" in the Accion filter
    const accionInput = field(page, 'Acción').input
    await accionInput.fill('login')

    // Click Filtrar
    await page.getByRole('button', { name: 'Filtrar' }).click()
    await page.waitForTimeout(1000)

    // All visible badges should contain "login"
    const badges = page.locator('tbody tr')
    const count = await badges.count()
    expect(count).toBeGreaterThan(0)

    for (let i = 0; i < count; i++) {
      const badgeText = await badges.nth(i).locator('span').first().textContent()
      // The accion column badge should contain "login"
      const rowText = await badges.nth(i).textContent()
      expect(rowText.toLowerCase()).toContain('login')
    }
  })

  // -- Limpiar filtros -------------------------------------------------------

  test('limpiar button resets filters', async ({ page }) => {
    const accionInput = field(page, 'Acción').input

    // Apply a filter first
    await accionInput.fill('login')
    await page.getByRole('button', { name: 'Filtrar' }).click()
    await page.waitForTimeout(1000)

    const filteredCount = await page.locator('tbody tr').count()

    // Click Limpiar
    await page.getByRole('button', { name: 'Limpiar' }).click()
    await page.waitForTimeout(1000)

    // Input should be cleared
    await expect(accionInput).toHaveValue('')

    // Results should reset (count may be >= filtered count)
    const resetCount = await page.locator('tbody tr').count()
    expect(resetCount).toBeGreaterThanOrEqual(filteredCount)
  })

  // -- Pagination info -------------------------------------------------------

  test('pagination info text is shown', async ({ page }) => {
    // The page shows "Pagina X de Y" when totalPages > 1,
    // or just the table when there is only one page.
    // We verify whichever state is present.

    const paginationText = page.getByText(/Página \d+ de \d+/i)
    const rows = page.locator('tbody tr')
    const rowCount = await rows.count()

    if (rowCount >= 20) {
      // With 20+ rows, pagination should be visible
      await expect(paginationText).toBeVisible()

      // Verify navigation buttons exist
      await expect(page.getByRole('button', { name: 'Anterior' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Siguiente' })).toBeVisible()
    } else {
      // Fewer than 20 entries — pagination may not be shown,
      // but the table should still have entries
      expect(rowCount).toBeGreaterThan(0)
    }
  })
})
