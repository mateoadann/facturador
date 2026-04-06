import { test, expect } from '@playwright/test'
import { execFileSync } from 'child_process'
import { USERS, field, login } from './helpers.js'

const CWD = '/Users/mateo/Documents/clientes/facturador/facturador_v2'
const DC = ['compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.dev.yml']

const TEST_EMAIL = 'e2e-test@facturador.local'

function dbExec(sql) {
  try {
    execFileSync('docker', [
      ...DC, 'exec', '-T', 'postgres',
      'psql', '-U', 'facturador', '-d', 'facturador', '-c', sql,
    ], { cwd: CWD })
  } catch { /* non-critical */ }
}

function cleanupTestUser() {
  dbExec(`DELETE FROM usuario WHERE email = '${TEST_EMAIL}';`)
}

test.describe('Usuarios', () => {
  test.beforeAll(() => cleanupTestUser())
  test.afterAll(() => cleanupTestUser())

  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/usuarios')
    await page.waitForTimeout(1000)
  })

  // ── Table ──────────────────────────────────────────────────────────────

  test('table loads with expected columns and known users', async ({ page }) => {
    for (const header of ['Nombre', 'Email', 'Rol', 'Estado', 'Dashboard sensible', 'Último Login', 'Acciones']) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }

    await expect(page.getByText(USERS.admin.email)).toBeVisible()
    await expect(page.getByText(USERS.operator.email)).toBeVisible()
    await expect(page.getByText(USERS.viewer.email)).toBeVisible()
  })

  // ── Create: modal opens ──────────────────────────────────────────────

  test('create user: modal opens with all fields', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo usuario/i }).click()

    await expect(page.getByRole('heading', { name: /nuevo usuario/i })).toBeVisible()

    await expect(field(page, 'Nombre').input).toBeVisible()
    await expect(field(page, 'Email').input).toBeVisible()
    await expect(field(page, 'Contraseña').input).toBeVisible()
    await expect(field(page, 'Rol').select).toBeVisible()
  })

  // ── Create: validation ───────────────────────────────────────────────

  test('create user: validation — submit empty shows error', async ({ page }) => {
    await page.getByRole('button', { name: /nuevo usuario/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo usuario/i })).toBeVisible()

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Usuario/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    // Backend returns "Email y contraseña son requeridos"
    await expect(page.getByText(/requerido/i).first()).toBeVisible({ timeout: 10_000 })
  })

  // ── Create: happy path ───────────────────────────────────────────────

  test('create user: happy path — fill form, save, verify appears', async ({ page }) => {
    cleanupTestUser()

    await page.getByRole('button', { name: /nuevo usuario/i }).click()
    await expect(page.getByRole('heading', { name: /nuevo usuario/i })).toBeVisible()

    await field(page, 'Nombre').input.fill('E2E Test User')
    await field(page, 'Email').input.fill(TEST_EMAIL)
    await field(page, 'Contraseña').input.fill('test1234secure')
    await field(page, 'Rol').select.selectOption('operator')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Nuevo Usuario/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Usuario creado correctamente/i).first()).toBeVisible({ timeout: 10_000 })

    // Verify appears in table
    await expect(page.getByText(TEST_EMAIL)).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText('E2E Test User')).toBeVisible()
  })

  // ── Edit user ────────────────────────────────────────────────────────

  test('edit user: modal pre-filled, change nombre, save', async ({ page }) => {
    const row = page.locator('tr', { hasText: TEST_EMAIL })
    await expect(row).toBeVisible({ timeout: 10_000 })
    await row.locator('button[title="Editar"]').click()

    await expect(page.getByRole('heading', { name: /editar usuario/i })).toBeVisible()

    // Email should be disabled in edit mode
    await expect(field(page, 'Email').input).toBeDisabled()

    // Nombre pre-filled
    await expect(field(page, 'Nombre').input).toHaveValue('E2E Test User')

    // Change nombre
    await field(page, 'Nombre').input.clear()
    await field(page, 'Nombre').input.fill('E2E Edited User')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: /Editar Usuario/ })
    await modal.getByRole('button', { name: 'Guardar' }).click()

    await expect(page.getByText(/Usuario actualizado correctamente/i).first()).toBeVisible({ timeout: 10_000 })

    // Verify updated name in table
    await expect(page.getByText('E2E Edited User')).toBeVisible({ timeout: 5_000 })
  })

  // ── Deactivate user ──────────────────────────────────────────────────

  test('deactivate user: badge changes to Inactivo', async ({ page }) => {
    const row = page.locator('tr', { hasText: TEST_EMAIL })
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Accept the confirm dialog
    page.on('dialog', (dialog) => dialog.accept())

    await row.locator('button[title="Desactivar"]').click()

    await expect(page.getByText(/Usuario desactivado/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(row.getByText('Inactivo')).toBeVisible()
  })

  // ── Activate user ────────────────────────────────────────────────────

  test('activate user: badge changes to Activo', async ({ page }) => {
    const row = page.locator('tr', { hasText: TEST_EMAIL })
    await expect(row).toBeVisible({ timeout: 10_000 })

    // Accept the confirm dialog (same as deactivate — source uses confirm() for both)
    page.on('dialog', (dialog) => dialog.accept())

    await row.locator('button[title="Activar"]').click()

    await expect(page.getByText(/Usuario activado/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(row.getByText('Activo')).toBeVisible()
  })

  // ── Cannot deactivate self ───────────────────────────────────────────

  test('cannot deactivate self — power button not present for current user row', async ({ page }) => {
    // The current user row has "(vos)" indicator
    const selfRow = page.locator('tr', { hasText: '(vos)' })
    await expect(selfRow).toBeVisible({ timeout: 10_000 })

    // Edit button should exist
    await expect(selfRow.locator('button[title="Editar"]')).toBeVisible()

    // Power (deactivate/activate) button should NOT exist — it's conditionally
    // not rendered for the current user (user.id !== currentUser?.id)
    await expect(selfRow.locator('button[title="Desactivar"]')).toHaveCount(0)
    await expect(selfRow.locator('button[title="Activar"]')).toHaveCount(0)
  })
})
