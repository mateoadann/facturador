/**
 * Shared E2E test helpers.
 *
 * The UI components (Input, Select, CurrencyInput, DatePicker) render as:
 *   <div class="flex flex-col ...">
 *     <label>Label Text</label>
 *     <input /> | <select /> | ...
 *   </div>
 * Labels have NO htmlFor, inputs have NO id — so getByLabel() won't work.
 */

export const USERS = {
  admin: { email: 'admin@facturador.local', password: 'admin123' },
  operator: { email: 'operador@facturador.local', password: 'operador123' },
  viewer: { email: 'viewer@facturador.local', password: 'viewer123' },
}

/** Locate input/select inside a label-based field container */
export function field(page, labelText) {
  const container = page.locator('.flex.flex-col', { hasText: labelText }).filter({
    has: page.locator(`> label:text-is("${labelText}")`),
  })
  return {
    input: container.locator('input').first(),
    select: container.locator('select').first(),
    container,
  }
}

/** Select an option whose visible text contains the given substring */
export async function selectOptionByText(selectLocator, substring) {
  const option = selectLocator.locator('option', { hasText: substring })
  const value = await option.first().getAttribute('value')
  await selectLocator.selectOption(value)
}

/** Clear localStorage and navigate to login */
export async function clearSession(page) {
  await page.goto('/')
  await page.evaluate(() => localStorage.clear())
}

/** Login with the given credentials */
export async function login(page, user = USERS.admin) {
  await clearSession(page)
  await page.goto('/login')
  await field(page, 'Email').input.fill(user.email)
  await field(page, 'Contraseña').input.fill(user.password)
  await page.getByRole('button', { name: /ingresar/i }).click()
  await page.waitForURL(/\/(dashboard|facturar)/, { timeout: 15_000 })
}
