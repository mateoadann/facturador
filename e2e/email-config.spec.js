import { test, expect } from '@playwright/test'
import { USERS, field, login } from './helpers.js'

test.describe('Email Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/email')
    await page.waitForTimeout(1000)
  })

  test('page loads with SMTP config card visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Servidor SMTP/i })).toBeVisible()
  })

  test('SMTP fields are present', async ({ page }) => {
    await expect(field(page, 'Host SMTP').input).toBeVisible()
    await expect(field(page, 'Puerto').input).toBeVisible()
    await expect(field(page, 'Usuario SMTP').input).toBeVisible()
    await expect(field(page, 'Email remitente').input).toBeVisible()
    await expect(field(page, 'Nombre remitente').input).toBeVisible()

    // Password field label varies by config state
    const passwordInput = page.locator('.flex.flex-col').filter({ hasText: /Contraseña/ }).locator('input').first()
    await expect(passwordInput).toBeVisible()
  })

  test('TLS and Email habilitado checkboxes are visible', async ({ page }) => {
    // Checkbox component renders: <button role="checkbox"> + <button>Label</button> as siblings
    // The accessible name is NOT associated, so we find by sibling text
    const tlsLabel = page.getByRole('button', { name: 'Usar TLS' })
    const habilitadoLabel = page.getByRole('button', { name: 'Email habilitado' })

    await expect(tlsLabel).toBeVisible()
    await expect(habilitadoLabel).toBeVisible()

    // The checkbox buttons (role=checkbox) are siblings — verify they exist
    const checkboxes = page.locator('button[role="checkbox"]')
    const count = await checkboxes.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })

  test('save SMTP config button exists', async ({ page }) => {
    await expect(
      page.getByRole('button', { name: /guardar configuración/i }).first()
    ).toBeVisible()
  })

  test('test connection button exists', async ({ page }) => {
    await expect(
      page.getByRole('button', { name: /testear conexión/i })
    ).toBeVisible()
  })

  test('email personalization card visible when configured', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Personalización del email/i })
    const isVisible = await heading.isVisible().catch(() => false)

    if (isVisible) {
      await expect(field(page, 'Asunto').input).toBeVisible()
      await expect(field(page, 'Saludo').input).toBeVisible()
      await expect(page.getByRole('button', { name: /vista previa/i })).toBeVisible()
    }
  })

  test('test email section has destination input and send button', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /Email de prueba/i })
    const isVisible = await heading.isVisible().catch(() => false)

    if (isVisible) {
      await expect(field(page, 'Email de destino').input).toBeVisible()
      await expect(page.getByRole('button', { name: /enviar prueba/i })).toBeVisible()
    }
  })
})
