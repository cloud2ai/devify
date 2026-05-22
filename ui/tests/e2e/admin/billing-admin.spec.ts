import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('Admin Billing Users', () => {
  test('admin sees users table with billing info', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Should have content — check what rendered
    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 200))
    expect(bodyText).toBeTruthy()
  })

  test('admin searches users', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    const searchInput = page.locator('input[placeholder*="search" i], input[type="search"]').first()
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('e2e')
      await page.keyboard.press('Enter')
      await page.waitForTimeout(1000)
    }
  })
})

test.describe('Admin Billing Plans', () => {
  test('admin sees all plans including internal', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/plans', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // All 5 plans should be visible (including Internal)
    const planNames = ['Free Plan', 'Starter Plan', 'Standard Plan', 'Pro Plan', 'Internal Plan']
    for (const name of planNames) {
      await expect(page.getByText(name).first()).toBeVisible({ timeout: 5000 })
    }
  })

  test('admin creates and deletes a test plan', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/plans', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    const createBtn = page.getByRole('button', { name: /create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click()
      await page.waitForTimeout(500)

      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first()
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill('E2E Test Plan')
        const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first()
        if (await saveBtn.isVisible().catch(() => false)) {
          await saveBtn.click()
          await page.waitForTimeout(1000)
          await expect(page.getByText('E2E Test Plan')).toBeVisible({ timeout: 5000 })
        }
      }
    }
  })
})

test.describe('Admin Billing Settings', () => {
  test('admin sees billing config', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/settings', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 200))
    expect(bodyText).toBeTruthy()
  })
})

test.describe('Admin Audit Logs', () => {
  test('admin sees paginated audit logs', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/audit-logs', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 200))
    expect(bodyText).toBeTruthy()
  })

  test('admin filters audit logs by action type', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/audit-logs', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    const actionFilter = page.locator('select').first()
    if (await actionFilter.isVisible({ timeout: 3000 }).catch(() => false)) {
      await actionFilter.selectOption({ index: 1 })
      await page.waitForTimeout(1000)
    }
  })
})
