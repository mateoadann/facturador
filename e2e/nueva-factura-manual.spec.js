import { test, expect } from '@playwright/test'

// ── Helpers ──────────────────────────────────────────────────────────────────

const CREDENTIALS = { email: 'admin@facturador.local', password: 'admin123' }
const BASE = 'http://localhost:5173'
const FACTURADOR_TEXT = 'Bavera'

/**
 * The UI components (Input, Select, CurrencyInput, DatePicker) render as:
 *   <div>
 *     <label>Label Text</label>
 *     <input /> | <select /> | <div><select/></div>
 *   </div>
 * Labels have NO htmlFor, inputs have NO id — so getByLabel() won't work.
 * This helper finds the parent container by label text, then targets the
 * input/select inside it.
 */
function field(page, labelText) {
  const container = page.locator('.flex.flex-col', { hasText: labelText }).filter({
    has: page.locator(`> label:text-is("${labelText}")`)
  })
  return {
    input: container.locator('input').first(),
    select: container.locator('select').first(),
    container,
  }
}

/** Select an option whose visible text contains the given substring */
async function selectOptionByText(selectLocator, substring) {
  const option = selectLocator.locator('option', { hasText: substring })
  const value = await option.first().getAttribute('value')
  await selectLocator.selectOption(value)
}

async function login(page) {
  await page.goto(`${BASE}/login`)
  // If already logged in, we'll be redirected to dashboard
  if (page.url().includes('/login')) {
    await field(page, 'Email').input.fill(CREDENTIALS.email)
    await field(page, 'Contraseña').input.fill(CREDENTIALS.password)
    await page.getByRole('button', { name: /ingresar/i }).click()
    await page.waitForURL(/\/(dashboard|facturar)/, { timeout: 15_000 })
  }
}

async function clearSession(page) {
  await page.goto(BASE)
  await page.evaluate(() => localStorage.clear())
}

async function navigateToFacturar(page) {
  if (!page.url().includes('/facturar')) {
    await page.locator('a[href="/facturar"]').first().click()
    await page.waitForURL(/\/facturar/, { timeout: 10_000 })
  }
}

async function openModal(page) {
  await page.getByRole('button', { name: /nueva factura/i }).click()
  await expect(page.getByRole('heading', { name: 'Nueva Factura' })).toBeVisible({ timeout: 5_000 })
  // Wait for dropdowns to load
  await page.waitForTimeout(1000)
}

// ── Tests ────────────────────────────────────────────────────────────────────

test.describe('Nueva Factura Manual', () => {
  test.beforeEach(async ({ page }) => {
    await clearSession(page)
    await login(page)
    await navigateToFacturar(page)
  })

  test('modal opens and shows all required fields', async ({ page }) => {
    await openModal(page)

    // Lote section
    await expect(page.getByText('Nuevo lote')).toBeVisible()
    await expect(page.getByText('Lote existente')).toBeVisible()
    await expect(field(page, 'Etiqueta del lote').input).toBeVisible()

    // Main fields
    await expect(field(page, 'Facturador').select).toBeVisible()
    await expect(field(page, 'Receptor').select).toBeVisible()
    await expect(field(page, 'Tipo comprobante').select).toBeVisible()
    await expect(field(page, 'Concepto').select).toBeVisible()

    // Dates
    await expect(field(page, 'Fecha emisión').input).toBeVisible()
    await expect(field(page, 'Fecha desde').input).toBeVisible()
    await expect(field(page, 'Fecha hasta').input).toBeVisible()
    await expect(field(page, 'Vto pago').input).toBeVisible()

    // Totals (disabled CurrencyInputs) — default is Factura C so IVA is hidden
    await expect(field(page, 'Importe total').input).toBeVisible()
    await expect(field(page, 'Importe neto').input).toBeVisible()
    await expect(field(page, 'IVA').input).not.toBeVisible()

    // Items section
    await expect(page.getByText('Items')).toBeVisible()
    await expect(field(page, 'Descripción #1').input).toBeVisible()

    // Footer buttons
    await expect(page.getByRole('button', { name: 'Cancelar' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Crear Factura' })).toBeVisible()
  })

  test('validation: error when facturador not selected', async ({ page }) => {
    await openModal(page)
    await page.getByRole('button', { name: 'Crear Factura' }).click()
    await expect(page.getByText(/seleccioná un facturador/i)).toBeVisible()
  })

  test('validation: etiqueta required for new lote', async ({ page }) => {
    await openModal(page)

    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })

    // Leave etiqueta empty → submit
    await page.getByRole('button', { name: 'Crear Factura' }).click()
    await expect(page.getByText(/etiqueta del lote es requerida/i)).toBeVisible()
  })

  test('validation: item description required', async ({ page }) => {
    await openModal(page)

    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })
    await field(page, 'Etiqueta del lote').input.fill('Test-Valid-Item')

    // Leave item description empty → submit
    await page.getByRole('button', { name: 'Crear Factura' }).click()
    await expect(page.getByText(/item 1: descripción requerida/i)).toBeVisible()
  })

  test('lote mode toggle: switch between new and existing', async ({ page }) => {
    await openModal(page)

    // Default: "Nuevo lote" → etiqueta input visible
    await expect(field(page, 'Etiqueta del lote').input).toBeVisible()

    // Switch to "Lote existente"
    await page.getByText('Lote existente').click()
    await expect(field(page, 'Seleccionar lote').select).toBeVisible()
    await expect(field(page, 'Etiqueta del lote').input).not.toBeVisible()

    // Switch back
    await page.getByText('Nuevo lote').click()
    await expect(field(page, 'Etiqueta del lote').input).toBeVisible()
  })

  test('items: add and remove items', async ({ page }) => {
    await openModal(page)

    // Start with 1 item
    await expect(field(page, 'Descripción #1').input).toBeVisible()
    await expect(field(page, 'Descripción #2').input).not.toBeVisible()

    // Add second item
    await page.getByRole('button', { name: /agregar/i }).click()
    await expect(field(page, 'Descripción #2').input).toBeVisible()

    // Add third item
    await page.getByRole('button', { name: /agregar/i }).click()
    await expect(field(page, 'Descripción #3').input).toBeVisible()

    // Remove second item
    const trashButtons = page.locator('button[title="Eliminar item"]')
    await trashButtons.nth(1).click()

    // Now 2 items: #1 and #2
    await expect(field(page, 'Descripción #1').input).toBeVisible()
    await expect(field(page, 'Descripción #2').input).toBeVisible()
    await expect(field(page, 'Descripción #3').input).not.toBeVisible()
  })

  test('totals: Factura C calculates with IVA=0', async ({ page }) => {
    await openModal(page)

    // Default tipo = Factura C (11) → IVA should be 0
    await expect(field(page, 'Tipo comprobante').select).toHaveValue('11')

    // Fill item: cantidad=2, precio=1000
    await field(page, 'Cantidad').input.fill('2')

    const precioInput = field(page, 'Precio unit.').input
    await precioInput.click()
    await precioInput.press('Control+a')
    await precioInput.pressSequentially('1000')

    // Wait for recalculation
    await page.waitForTimeout(500)

    // Factura C: IVA field is hidden, total should equal neto (2000)
    await expect(field(page, 'IVA').input).not.toBeVisible()
    const totalInput = field(page, 'Importe total').input
    const totalValue = await totalInput.inputValue()
    const netoInput = field(page, 'Importe neto').input
    const netoValue = await netoInput.inputValue()
    expect(totalValue).toBe(netoValue)
  })

  test('totals: Factura A calculates with IVA 21%', async ({ page }) => {
    await openModal(page)

    // Switch to Factura A
    await field(page, 'Tipo comprobante').select.selectOption('1')

    // Fill item: cantidad=1, precio=10000
    await field(page, 'Cantidad').input.fill('1')

    const precioInput = field(page, 'Precio unit.').input
    await precioInput.click()
    await precioInput.press('Control+a')
    await precioInput.pressSequentially('10000')

    await page.waitForTimeout(300)

    // neto=10000, IVA=2100 (21%), total=12100
    const ivaInput = field(page, 'IVA').input
    await expect(ivaInput).not.toHaveValue('0')
  })

  test('nota de crédito: shows associated voucher fields', async ({ page }) => {
    await openModal(page)

    // Select Nota Crédito A (value=3)
    await field(page, 'Tipo comprobante').select.selectOption('3')

    // Associated voucher fields should appear
    await expect(field(page, 'Cbte asoc tipo').input).toBeVisible()
    await expect(field(page, 'Cbte asoc pto vta').input).toBeVisible()
    await expect(field(page, 'Cbte asoc nro').input).toBeVisible()
  })

  test('nota de crédito: validation requires associated voucher', async ({ page }) => {
    await openModal(page)

    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })
    await field(page, 'Tipo comprobante').select.selectOption('3') // Nota Crédito A
    await field(page, 'Etiqueta del lote').input.fill('Test-NC-Validation')

    // Fill item
    await field(page, 'Descripción #1').input.fill('Ajuste')
    await field(page, 'Cantidad').input.fill('1')
    const precioInput = field(page, 'Precio unit.').input
    await precioInput.click()
    await precioInput.press('Control+a')
    await precioInput.pressSequentially('500')

    // Leave cbte_asoc fields empty → submit
    await page.getByRole('button', { name: 'Crear Factura' }).click()
    await expect(page.getByText(/notas se requiere comprobante asociado/i)).toBeVisible()
  })

  test('modal resets form on close and reopen', async ({ page }) => {
    await openModal(page)

    // Fill some data
    await field(page, 'Etiqueta del lote').input.fill('Should-Be-Cleared')
    await field(page, 'Descripción #1').input.fill('Should-Be-Cleared-Too')

    // Close modal
    await page.getByRole('button', { name: 'Cancelar' }).click()
    await expect(page.getByRole('heading', { name: 'Nueva Factura' })).not.toBeVisible()

    // Reopen
    await openModal(page)

    // Fields should be reset
    await expect(field(page, 'Etiqueta del lote').input).toHaveValue('')
    await expect(field(page, 'Descripción #1').input).toHaveValue('')
  })

  test('happy path: create Factura C with new lote (Servicios)', async ({ page }) => {
    const etiqueta = `E2E-Test-${Date.now()}`

    await openModal(page)

    // 1. Lote: nueva etiqueta
    await field(page, 'Etiqueta del lote').input.fill(etiqueta)

    // 2. Facturador: Bavera
    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)

    // 3. Receptor: first available
    await field(page, 'Receptor').select.selectOption({ index: 1 })

    // 4. Tipo comprobante: Factura C (default=11) ✓
    // 5. Concepto: Servicios (default=2) ✓

    // 6. Fill item #1
    await field(page, 'Descripción #1').input.fill('Servicio de consultoría E2E')
    await field(page, 'Cantidad').input.fill('3')
    const precioInput = field(page, 'Precio unit.').input
    await precioInput.click()
    await precioInput.press('Control+a')
    await precioInput.pressSequentially('5000')

    // 7. Add second item
    await page.getByRole('button', { name: /agregar/i }).click()
    await field(page, 'Descripción #2').input.fill('Análisis de datos E2E')

    // Fill second item fields
    const cantidadInputs = page.locator('.flex.flex-col').filter({
      has: page.locator('> label:text-is("Cantidad")')
    }).locator('input')
    await cantidadInputs.nth(1).fill('1')

    const precioInputs = page.locator('.flex.flex-col').filter({
      has: page.locator('> label:text-is("Precio unit.")')
    }).locator('input')
    await precioInputs.nth(1).click()
    await precioInputs.nth(1).press('Control+a')
    await precioInputs.nth(1).pressSequentially('2500')

    // 8. Submit
    await page.getByRole('button', { name: 'Crear Factura' }).click()

    // 9. Verify success toast
    await expect(page.getByText(/factura creada correctamente/i)).toBeVisible({ timeout: 15_000 })

    // 10. Modal should close
    await expect(page.getByRole('heading', { name: 'Nueva Factura' })).not.toBeVisible({ timeout: 5_000 })
  })

  test('happy path: create Factura A with IVA 21% (Productos)', async ({ page }) => {
    const etiqueta = `E2E-FactA-${Date.now()}`

    await openModal(page)

    await field(page, 'Etiqueta del lote').input.fill(etiqueta)
    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })
    await field(page, 'Tipo comprobante').select.selectOption('1') // Factura A
    await field(page, 'Concepto').select.selectOption('1') // Productos

    // Fill item
    await field(page, 'Descripción #1').input.fill('Producto de prueba E2E')
    await field(page, 'Cantidad').input.fill('10')
    const precioInput = field(page, 'Precio unit.').input
    await precioInput.click()
    await precioInput.press('Control+a')
    await precioInput.pressSequentially('1500')

    // Submit
    await page.getByRole('button', { name: 'Crear Factura' }).click()

    // Verify success
    await expect(page.getByText(/factura creada correctamente/i)).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('heading', { name: 'Nueva Factura' })).not.toBeVisible({ timeout: 5_000 })
  })

  test('tipo C hides IVA fields, tipo A shows them', async ({ page }) => {
    await openModal(page)

    // Default is Factura C (value 11) → IVA fields should be hidden
    await expect(field(page, 'Tipo comprobante').select).toHaveValue('11')

    // IVA select in items should NOT be visible
    await expect(field(page, 'IVA').select).not.toBeVisible()
    // IVA $ label should NOT be visible
    await expect(page.locator('label:text-is("IVA $")')).not.toBeVisible()
    // IVA total CurrencyInput should NOT be visible
    await expect(field(page, 'IVA').input).not.toBeVisible()

    // Switch to Factura A (value 1)
    await field(page, 'Tipo comprobante').select.selectOption('1')

    // IVA select in items should now be visible
    await expect(field(page, 'IVA').select).toBeVisible()
    // IVA $ label should be visible
    await expect(page.locator('label:text-is("IVA $")')).toBeVisible()
    // IVA total CurrencyInput should be visible
    await expect(field(page, 'IVA').input).toBeVisible()

    // Switch back to Factura C (value 11) → hidden again
    await field(page, 'Tipo comprobante').select.selectOption('11')

    await expect(field(page, 'IVA').select).not.toBeVisible()
    await expect(page.locator('label:text-is("IVA $")')).not.toBeVisible()
    await expect(field(page, 'IVA').input).not.toBeVisible()
  })

  test('duplicate etiqueta: shows backend error', async ({ page }) => {
    const etiqueta = `E2E-Dupe-${Date.now()}`

    // Create first factura
    await openModal(page)
    await field(page, 'Etiqueta del lote').input.fill(etiqueta)
    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })
    await field(page, 'Descripción #1').input.fill('Primera factura')
    await field(page, 'Cantidad').input.fill('1')
    const precio1 = field(page, 'Precio unit.').input
    await precio1.click()
    await precio1.press('Control+a')
    await precio1.pressSequentially('100')
    await page.getByRole('button', { name: 'Crear Factura' }).click()
    await expect(page.getByText(/factura creada correctamente/i)).toBeVisible({ timeout: 15_000 })

    // Try second with same etiqueta
    await openModal(page)
    await field(page, 'Etiqueta del lote').input.fill(etiqueta)
    await selectOptionByText(field(page, 'Facturador').select, FACTURADOR_TEXT)
    await field(page, 'Receptor').select.selectOption({ index: 1 })
    await field(page, 'Descripción #1').input.fill('Segunda factura')
    await field(page, 'Cantidad').input.fill('1')
    const precio2 = field(page, 'Precio unit.').input
    await precio2.click()
    await precio2.press('Control+a')
    await precio2.pressSequentially('200')
    await page.getByRole('button', { name: 'Crear Factura' }).click()

    // Should show duplicate error
    await expect(page.getByText(/etiqueta.*ya existe|duplicad/i)).toBeVisible({ timeout: 10_000 })
  })
})
