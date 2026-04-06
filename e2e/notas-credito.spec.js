import { test, expect } from '@playwright/test'
import { USERS, field, clearSession, login } from './helpers.js'

test.describe('Notas de Crédito', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, USERS.admin)
    await page.goto('/notas-credito')
    await page.waitForTimeout(1500)
  })

  // ── Page loads ──────────────────────────────────────────────────────────

  test('page loads with title and table visible', async ({ page }) => {
    // Header title should be visible
    await expect(page.getByText('Notas de Crédito').first()).toBeVisible()

    // Table columns specific to notas de crédito
    for (const header of [
      'Facturador',
      'Receptor',
      'Comprobante Asociado',
      'Fecha',
      'Importe',
      'Estado',
      'Acciones',
    ]) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
    // "Comprobante" needs exact match to avoid matching "Comprobante Asociado"
    await expect(page.getByRole('columnheader', { name: 'Comprobante', exact: true })).toBeVisible()

    // Either data rows or the empty state message should appear
    const tableBody = page.locator('tbody')
    await expect(tableBody).toBeVisible({ timeout: 10_000 })
  })

  // ── Estado filter ───────────────────────────────────────────────────────

  test('Estado filter dropdown is visible and interactive', async ({ page }) => {
    // The select with "Todos los estados" default should be visible
    const estadoSelect = page.locator('select').filter({ hasText: 'Todos los estados' })
    await expect(estadoSelect).toBeVisible()

    // Select "Autorizado" option
    await estadoSelect.selectOption('autorizado')
    await expect(estadoSelect).toHaveValue('autorizado')

    // Select "Error" option
    await estadoSelect.selectOption('error')
    await expect(estadoSelect).toHaveValue('error')

    // Select "Pendiente" option
    await estadoSelect.selectOption('pendiente')
    await expect(estadoSelect).toHaveValue('pendiente')

    // Reset to "Todos"
    await estadoSelect.selectOption('')
    await expect(estadoSelect).toHaveValue('')
  })

  // ── Nueva Nota de Crédito button ────────────────────────────────────────

  test('Nueva Nota de Crédito button exists', async ({ page }) => {
    const btn = page.getByRole('button', { name: /Nueva Nota de Crédito/i })
    await expect(btn).toBeVisible()
  })

  // ── Info card ───────────────────────────────────────────────────────────

  test('info card with instructions is visible', async ({ page }) => {
    // The info card explains how to create notas de crédito
    await expect(
      page.getByText(/Las notas de crédito se pueden crear desde la sección/i)
    ).toBeVisible()

    // It should mention the relevant comprobante types
    await expect(page.getByText(/NC A/)).toBeVisible()
    await expect(page.getByText(/NC B/)).toBeVisible()
    await expect(page.getByText(/NC C/)).toBeVisible()
  })
})
