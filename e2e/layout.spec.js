import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Layout & Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await clearSession(page)
  })

  // ── Sidebar navigation ──────────────────────────────────────────────────

  test('sidebar: all navigation links visible for admin', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    // FACTURACION section
    await expect(sidebar.locator('a[href="/facturar"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/facturas"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/notas-credito"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/consultar-comprobantes"]')).toBeVisible()

    // CONFIGURACION section
    await expect(sidebar.locator('a[href="/facturadores"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/receptores"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/email"]')).toBeVisible()

    // ADMINISTRACION section
    await expect(sidebar.locator('a[href="/usuarios"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/auditoria"]')).toBeVisible()
    await expect(sidebar.locator('a[href="/ayuda"]')).toBeVisible()

    // Dashboard
    await expect(sidebar.locator('a[href="/dashboard"]')).toBeVisible()
  })

  // ── Collapse / Expand ───────────────────────────────────────────────────

  test('sidebar: collapse toggle hides text labels', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    // Verify labels are visible before collapsing
    await expect(sidebar.getByText('Facturar')).toBeVisible()
    await expect(sidebar.getByText('Facturadores')).toBeVisible()

    // Click collapse button
    await sidebar.locator('button[title="Colapsar sidebar"]').click()

    // Labels should be hidden, but links still present
    await expect(sidebar.getByText('Facturar')).not.toBeVisible()
    await expect(sidebar.getByText('Facturadores')).not.toBeVisible()
    await expect(sidebar.locator('a[href="/facturar"]')).toBeVisible()
  })

  test('sidebar: expand restores text labels', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    // Collapse first
    await sidebar.locator('button[title="Colapsar sidebar"]').click()
    await expect(sidebar.getByText('Facturar')).not.toBeVisible()

    // Expand
    await sidebar.locator('button[title="Expandir sidebar"]').click()

    // Labels should be visible again
    await expect(sidebar.getByText('Facturar')).toBeVisible()
    await expect(sidebar.getByText('Facturadores')).toBeVisible()
    await expect(sidebar.getByText('Usuarios')).toBeVisible()
  })

  // ── Dark mode ───────────────────────────────────────────────────────────

  test('dark mode toggle: switches theme class', async ({ page }) => {
    await login(page, USERS.admin)

    const html = page.locator('html')
    const darkModeSwitch = page.locator('button[role="switch"]')

    // Start in light mode — html should NOT have "dark" class
    await expect(html).not.toHaveClass(/dark/)

    // Toggle dark mode on
    await darkModeSwitch.click()
    await expect(html).toHaveClass(/dark/)

    // Toggle dark mode off
    await darkModeSwitch.click()
    await expect(html).not.toHaveClass(/dark/)
  })

  // ── Header ──────────────────────────────────────────────────────────────

  test('header: page title matches current route', async ({ page }) => {
    await login(page, USERS.admin)

    // Dashboard
    await page.goto('/dashboard')
    await expect(page.locator('header h1')).toHaveText('Dashboard')

    // Facturadores
    await page.locator('aside a[href="/facturadores"]').click()
    await page.waitForURL(/\/facturadores/)
    await expect(page.locator('header h1')).toHaveText('Facturadores')

    // Receptores
    await page.locator('aside a[href="/receptores"]').click()
    await page.waitForURL(/\/receptores/)
    await expect(page.locator('header h1')).toHaveText('Receptores')

    // Usuarios
    await page.locator('aside a[href="/usuarios"]').click()
    await page.waitForURL(/\/usuarios/)
    await expect(page.locator('header h1')).toHaveText('Usuarios')
  })

  // ── User info ───────────────────────────────────────────────────────────

  test('sidebar: user info shows name and tenant', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    // The bottom section shows user name/email and tenant name
    // User name or email should be visible
    const userInfoSection = sidebar.locator('.border-t')
    await expect(userInfoSection).toBeVisible()

    // There should be two text elements: user name and tenant name
    const userName = userInfoSection.locator('p').first()
    const tenantName = userInfoSection.locator('p').nth(1)

    await expect(userName).toBeVisible()
    await expect(userName).not.toHaveText('')
    await expect(tenantName).toBeVisible()
    await expect(tenantName).not.toHaveText('')
  })

  // ── Bottom actions ──────────────────────────────────────────────────────

  test('sidebar: "Cerrar sesion" and "Cambiar contrasena" buttons visible', async ({ page }) => {
    await login(page, USERS.admin)

    const sidebar = page.locator('aside')

    await expect(sidebar.getByText('Cerrar sesión')).toBeVisible()
    await expect(sidebar.getByText('Cambiar contraseña')).toBeVisible()
  })
})
