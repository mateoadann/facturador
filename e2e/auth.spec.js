import { test, expect } from '@playwright/test'
import { execFileSync } from 'child_process'
import { USERS, field, clearSession, login } from './helpers.js'

const CWD = '/Users/mateo/Documents/clientes/facturador/facturador_v2'
const DC = ['compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.dev.yml']

/** Run a SQL command via docker psql */
function dbExec(sql) {
  try {
    execFileSync('docker', [
      ...DC, 'exec', '-T', 'postgres',
      'psql', '-U', 'facturador', '-d', 'facturador', '-c', sql,
    ], { cwd: CWD })
  } catch { /* non-critical */ }
}

/** Reset password for a user via backend container */
function resetPassword(email, password) {
  const script = `
from app import create_app
from app.extensions import db
from app.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(email='${email}').first()
    if u:
        u.set_password('${password}')
        u.login_attempts = 0
        u.locked_until = None
        db.session.commit()
        print(f'Password reset for {u.email}')
`
  try {
    execFileSync('docker', [
      ...DC, 'exec', '-T', 'api', 'python', '-c', script,
    ], { cwd: CWD })
  } catch { /* non-critical */ }
}

test.describe('Auth & Session', () => {
  // Ensure all test users have known passwords before running
  test.beforeAll(() => {
    resetPassword(USERS.admin.email, USERS.admin.password)
    resetPassword(USERS.operator.email, USERS.operator.password)
    resetPassword(USERS.viewer.email, USERS.viewer.password)
  })

  test.beforeEach(async ({ page }) => {
    await clearSession(page)
  })

  // ── Login ────────────────────────────────────────────────────────────────

  test('login happy path: valid credentials redirect to dashboard', async ({ page }) => {
    await page.goto('/login')

    await field(page, 'Email').input.fill(USERS.admin.email)
    await field(page, 'Contraseña').input.fill(USERS.admin.password)
    await page.getByRole('button', { name: /ingresar/i }).click()

    await page.waitForURL(/\/dashboard/, { timeout: 15_000 })
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })

  test('login error: invalid credentials shows error message', async ({ page }) => {
    await page.goto('/login')

    await field(page, 'Email').input.fill(USERS.admin.email)
    await field(page, 'Contraseña').input.fill('wrongpassword')
    await page.getByRole('button', { name: /ingresar/i }).click()

    await expect(page.getByText(/credenciales inválidas/i)).toBeVisible({ timeout: 10_000 })
    expect(page.url()).toContain('/login')
  })

  test('login error: invalid email format shows browser validation', async ({ page }) => {
    await page.goto('/login')

    const emailInput = field(page, 'Email').input
    await emailInput.fill('not-an-email')
    await field(page, 'Contraseña').input.fill('somepassword')
    await page.getByRole('button', { name: /ingresar/i }).click()

    // HTML5 type="email" triggers browser-native validation
    // The form should NOT submit — we verify by checking we're still on login
    // and no API error appeared (zod validation won't fire because browser blocks)
    await page.waitForTimeout(500)
    expect(page.url()).toContain('/login')

    // Verify the input is marked as invalid via HTML5 constraint API
    const isInvalid = await emailInput.evaluate((el) => !el.checkValidity())
    expect(isInvalid).toBe(true)
  })

  test('login error: empty password shows validation', async ({ page }) => {
    await page.goto('/login')

    await field(page, 'Email').input.fill(USERS.admin.email)
    await page.getByRole('button', { name: /ingresar/i }).click()

    await expect(page.getByText(/contraseña requerida/i)).toBeVisible()
  })

  test('login: auto-redirect to dashboard if already authenticated', async ({ page }) => {
    await login(page)
    expect(page.url()).toContain('/dashboard')

    await page.goto('/login')
    await page.waitForURL(/\/dashboard/, { timeout: 10_000 })
  })

  // ── Multi-role login ─────────────────────────────────────────────────────

  test('login as operator: access granted', async ({ page }) => {
    await login(page, USERS.operator)
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })

  test('login as viewer: access granted', async ({ page }) => {
    await login(page, USERS.viewer)
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })

  // ── Logout ───────────────────────────────────────────────────────────────

  test('logout: clears session and redirects to login', async ({ page }) => {
    await login(page)

    await page.getByRole('button', { name: /cerrar sesión/i }).click()
    await page.waitForURL(/\/login/, { timeout: 10_000 })

    // Verify protected pages redirect to login
    await page.goto('/dashboard')
    await page.waitForURL(/\/login/, { timeout: 10_000 })
  })

  // ── Change Password ──────────────────────────────────────────────────────

  test('change password: modal opens from sidebar', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()

    await expect(page.getByRole('heading', { name: /cambiar contraseña/i })).toBeVisible()
    await expect(field(page, 'Contraseña actual').input).toBeVisible()
    await expect(field(page, 'Nueva contraseña').input).toBeVisible()
    await expect(field(page, 'Confirmar nueva contraseña').input).toBeVisible()
  })

  test('change password: validation — all fields required', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()
    await expect(page.getByRole('heading', { name: /cambiar contraseña/i })).toBeVisible()

    // Click the submit button INSIDE the modal (not the sidebar one)
    const modal = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    await expect(page.getByText(/contraseña actual es requerida/i)).toBeVisible()
    await expect(page.getByText(/nueva contraseña es requerida/i)).toBeVisible()
  })

  test('change password: validation — minimum 8 characters', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill('admin123')
    await field(page, 'Nueva contraseña').input.fill('short')
    await field(page, 'Confirmar nueva contraseña').input.fill('short')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    await expect(page.getByText(/mínimo 8 caracteres/i)).toBeVisible()
  })

  test('change password: validation — passwords must match', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill('admin123')
    await field(page, 'Nueva contraseña').input.fill('newpassword123')
    await field(page, 'Confirmar nueva contraseña').input.fill('differentpassword')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    await expect(page.getByText(/contraseñas no coinciden/i)).toBeVisible()
  })

  test('change password: error — wrong current password', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill('wrongcurrent')
    await field(page, 'Nueva contraseña').input.fill('newpassword123')
    await field(page, 'Confirmar nueva contraseña').input.fill('newpassword123')

    const modal = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    // Error shows in both toast and modal — use .first() to avoid strict mode
    await expect(page.getByText(/contraseña actual incorrecta/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('change password: happy path — change and revert', async ({ page }) => {
    const originalPassword = USERS.admin.password
    const newPassword = 'tempnewpass123'

    await login(page)

    // Change to new password
    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill(originalPassword)
    await field(page, 'Nueva contraseña').input.fill(newPassword)
    await field(page, 'Confirmar nueva contraseña').input.fill(newPassword)

    const modal = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    await expect(page.getByText(/contraseña actualizada correctamente/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('heading', { name: /cambiar contraseña/i })).not.toBeVisible()

    // Logout and login with new password
    await page.getByRole('button', { name: /cerrar sesión/i }).click()
    await page.waitForURL(/\/login/, { timeout: 10_000 })

    await field(page, 'Email').input.fill(USERS.admin.email)
    await field(page, 'Contraseña').input.fill(newPassword)
    await page.getByRole('button', { name: /ingresar/i }).click()
    await page.waitForURL(/\/dashboard/, { timeout: 15_000 })

    // Revert password back to original
    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill(newPassword)
    await field(page, 'Nueva contraseña').input.fill(originalPassword)
    await field(page, 'Confirmar nueva contraseña').input.fill(originalPassword)

    const modal2 = page.locator('[class*="fixed"]').filter({ hasText: 'Cambiar Contraseña' })
    await modal2.getByRole('button', { name: 'Cambiar Contraseña' }).click()

    await expect(page.getByText(/contraseña actualizada correctamente/i)).toBeVisible({ timeout: 10_000 })
  })

  test('change password: modal resets on cancel', async ({ page }) => {
    await login(page)

    await page.locator('button[title="Cambiar contraseña"]').click()

    await field(page, 'Contraseña actual').input.fill('something')
    await field(page, 'Nueva contraseña').input.fill('something')

    await page.getByRole('button', { name: 'Cancelar' }).click()
    await expect(page.getByRole('heading', { name: /cambiar contraseña/i })).not.toBeVisible()

    // Reopen — should be clean
    await page.locator('button[title="Cambiar contraseña"]').click()
    await expect(field(page, 'Contraseña actual').input).toHaveValue('')
    await expect(field(page, 'Nueva contraseña').input).toHaveValue('')
    await expect(field(page, 'Confirmar nueva contraseña').input).toHaveValue('')
  })

  // ── Login lockout (LAST — mutates DB state) ──────────────────────────────

  test('login lockout: 5 failed attempts blocks the account', async ({ page }) => {
    // Ensure viewer is unlocked
    resetPassword(USERS.viewer.email, USERS.viewer.password)

    await page.goto('/login')

    // 5 failed attempts
    for (let i = 0; i < 5; i++) {
      await field(page, 'Email').input.fill(USERS.viewer.email)
      await field(page, 'Contraseña').input.fill('wrongpassword')
      await page.getByRole('button', { name: /ingresar/i }).click()

      await expect(
        page.getByText(/credenciales inválidas|cuenta bloqueada/i)
      ).toBeVisible({ timeout: 10_000 })

      await field(page, 'Email').input.clear()
      await field(page, 'Contraseña').input.clear()
    }

    // 6th attempt with correct password — should still be locked
    await field(page, 'Email').input.fill(USERS.viewer.email)
    await field(page, 'Contraseña').input.fill(USERS.viewer.password)
    await page.getByRole('button', { name: /ingresar/i }).click()

    await expect(page.getByText(/cuenta bloqueada/i)).toBeVisible({ timeout: 10_000 })

    // Cleanup
    resetPassword(USERS.viewer.email, USERS.viewer.password)
  })

  // Ensure passwords are reset after all tests
  test.afterAll(() => {
    resetPassword(USERS.admin.email, USERS.admin.password)
    resetPassword(USERS.viewer.email, USERS.viewer.password)
  })
})
