import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Facturar — Import CSV Modal', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/facturar')
    await page.waitForTimeout(1500)
  })

  // ── Modal opens ──────────────────────────────────────────────────────

  test('Import CSV modal opens when clicking Importar CSV button', async ({ page }) => {
    await page.getByRole('button', { name: /Importar CSV/i }).click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Importar Facturas/ })
    await expect(modal).toBeVisible({ timeout: 10_000 })
    await expect(modal.getByText('Importar Facturas')).toBeVisible()
  })

  // ── Modal has file upload, etiqueta, facturador selector ─────────────

  test('modal has file upload area, etiqueta input and facturador selector', async ({ page }) => {
    await page.getByRole('button', { name: /Importar CSV/i }).click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Importar Facturas/ })
    await expect(modal).toBeVisible({ timeout: 10_000 })

    // Step 1: file upload area with CSV instructions
    await expect(modal.getByText('1. Seleccionar archivo CSV')).toBeVisible()
    await expect(modal.locator('input[type="file"][accept=".csv"]')).toBeAttached()

    // Step 2: facturador selector
    await expect(modal.getByText('2. Seleccionar facturador')).toBeVisible()
    const facturadorSelect = modal.locator('select').filter({ hasText: /Seleccionar facturador/ })
    await expect(facturadorSelect).toBeVisible()

    // Step 4: etiqueta input
    await expect(modal.getByText(/Etiqueta del lote/)).toBeVisible()
  })

  // ── Template download section ────────────────────────────────────────

  test('modal has template download section', async ({ page }) => {
    await page.getByRole('button', { name: /Importar CSV/i }).click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Importar Facturas/ })
    await expect(modal).toBeVisible({ timeout: 10_000 })

    // Template accordion header
    const templateBtn = modal.getByText('0. Descargar template XLSX')
    await expect(templateBtn).toBeVisible()

    // Expand the template section
    await templateBtn.click()

    // Download button should appear
    await expect(
      modal.getByRole('button', { name: /Descargar template .xlsx/i })
    ).toBeVisible({ timeout: 5_000 })
  })

  // ── Modal closes on cancel ───────────────────────────────────────────

  test('modal closes when clicking Cancelar', async ({ page }) => {
    await page.getByRole('button', { name: /Importar CSV/i }).click()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Importar Facturas/ })
    await expect(modal).toBeVisible({ timeout: 10_000 })

    // Click Cancelar inside the modal
    await modal.getByRole('button', { name: 'Cancelar' }).click()

    // Modal should disappear
    await expect(modal).not.toBeVisible({ timeout: 5_000 })
  })
})
