import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Cross-role Permissions', () => {
  test.beforeEach(async ({ page }) => {
    await clearSession(page)
  })

  // ── Admin visibility ────────────────────────────────────────────────────

  test('admin: can see Usuarios and Auditoria links in sidebar', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    await expect(sidebar.locator('a[href="/usuarios"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/auditoria"]')).toBeVisible()

    // Verify ADMINISTRACION group label is shown
    await expect(sidebar.getByText('ADMINISTRACIÓN')).toBeVisible()
  })

  // ── Operator visibility ─────────────────────────────────────────────────

  test('operator: cannot see Usuarios and Auditoria, CAN see Facturar and Facturadores', async ({ page }) => {
    await login(page, USERS.operator)

    const sidebar = page.locator('aside')

    // Operator should NOT see admin-only links
    await expect(sidebar.locator('a[href="/usuarios"]')).not.toBeVisible()
    await expect(sidebar.locator('a[href="/auditoria"]')).not.toBeVisible()

    // Operator CAN see operational links
    await expect(sidebar.locator('a[href="/facturar"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/facturadores"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/facturas"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/receptores"]')).toBeVisible()
  })

  // ── Viewer read-only ────────────────────────────────────────────────────

  test('viewer: cannot see "Nuevo Facturador" button on /facturadores page', async ({ page }) => {
    await login(page, USERS.viewer)

    await page.goto('/facturadores')
    await page.waitForURL(/\/facturadores/)
    await page.waitForTimeout(1000)

    // Viewer has facturadores:ver but NOT facturadores:crear
    // The button is gated behind PermissionGate
    await expect(
      page.getByRole('button', { name: /nuevo facturador/i })
    ).not.toBeVisible()
  })

  // ── Direct URL access ───────────────────────────────────────────────────

  test('viewer: direct URL access to /usuarios redirects away or shows no data', async ({ page }) => {
    await login(page, USERS.viewer)

    await page.goto('/usuarios')

    // Viewer does not have usuarios:ver permission.
    // The app should either redirect away from /usuarios or not render the page content.
    // We check that the Usuarios heading does NOT appear in the main content area.
    await page.waitForTimeout(2_000)

    const isOnUsuarios = page.url().includes('/usuarios')

    if (!isOnUsuarios) {
      // Redirected away — that's correct behavior
      expect(page.url()).not.toContain('/usuarios')
    } else {
      // If still on /usuarios, the page should not show the user management table
      await expect(
        page.locator('header h1', { hasText: 'Usuarios' })
      ).not.toBeVisible()
    }
  })
})
