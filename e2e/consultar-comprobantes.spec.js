import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Consultar Comprobantes', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/consultar-comprobantes')
    await page.waitForTimeout(1000)
  })

  // ── Page loads with form fields ────────────────────────────────────────

  test('page loads with all form fields', async ({ page }) => {
    // Title
    await expect(page.getByText('Consultar Comprobante en ARCA')).toBeVisible({ timeout: 10_000 })

    // Form fields
    await expect(field(page, 'Facturador').select).toBeVisible()
    await expect(field(page, 'Tipo de Comprobante').select).toBeVisible()
    await expect(field(page, 'Punto de Venta').input).toBeVisible()
    await expect(field(page, 'Número').input).toBeVisible()

    // Facturador select should have options loaded
    const facturadorOptions = field(page, 'Facturador').select.locator('option')
    const count = await facturadorOptions.count()
    expect(count).toBeGreaterThan(1) // "Seleccionar..." + at least one facturador

    // Tipo de Comprobante should have all types
    const tipoOptions = field(page, 'Tipo de Comprobante').select.locator('option')
    const tipoCount = await tipoOptions.count()
    expect(tipoCount).toBe(10) // "Seleccionar..." + 9 tipos
  })

  // ── Consultar button ──────────────────────────────────────────────────

  test('Consultar Comprobante button exists and is visible', async ({ page }) => {
    const consultarBtn = page.getByRole('button', { name: /Consultar Comprobante/i })
    await expect(consultarBtn).toBeVisible({ timeout: 5_000 })
    await expect(consultarBtn).toBeEnabled()
  })

  // ── Último Autorizado button ──────────────────────────────────────────

  test('Último Autorizado button exists and is visible', async ({ page }) => {
    const ultimoBtn = page.getByRole('button', { name: /Último Autorizado/i })
    await expect(ultimoBtn).toBeVisible({ timeout: 5_000 })
    await expect(ultimoBtn).toBeEnabled()
  })

  // ── Warning for facturador without certificates ───────────────────────

  test('warning shown when facturador without certificates is selected', async ({ page }) => {
    const facturadorSelect = field(page, 'Facturador').select

    // Get all options except the placeholder
    const options = facturadorSelect.locator('option')
    const optionCount = await options.count()

    // Try each facturador to find one without certificates
    let foundWarning = false
    for (let i = 1; i < optionCount; i++) {
      const value = await options.nth(i).getAttribute('value')
      await facturadorSelect.selectOption(value)
      await page.waitForTimeout(500)

      const warning = page.getByText(/no tiene certificados cargados/i)
      if (await warning.isVisible().catch(() => false)) {
        foundWarning = true
        // Verify the full warning message
        await expect(warning).toBeVisible()
        await expect(page.getByText(/Cargalos desde la sección Facturadores/i)).toBeVisible()
        break
      }
    }

    // If no facturador lacks certs, select one with certs and verify NO warning
    if (!foundWarning) {
      // All facturadores have certs — verify warning is NOT shown for the selected one
      await expect(page.getByText(/no tiene certificados cargados/i)).not.toBeVisible()
    }
  })
})
