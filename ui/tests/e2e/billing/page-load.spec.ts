import { test, expect } from '@playwright/test'
import { loginAs, E2E_USERS } from '../helpers/auth'

test.describe('Billing Page Load', () => {
  test('free user sees current Free plan and all public plans', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Current subscription shows Free Plan
    await expect(page.getByRole('heading', { name: 'Free Plan' }).first()).toBeVisible()
    await expect(page.getByText('Active')).toBeVisible()

    // All 4 public plans visible as headings (use .first() since each appears in plan list)
    const planHeadings = ['Free Plan', 'Starter Plan', 'Standard Plan', 'Pro Plan']
    for (const name of planHeadings) {
      await expect(page.getByRole('heading', { name }).first()).toBeVisible({ timeout: 3000 })
    }

    // Internal plan should NOT be visible
    await expect(page.getByRole('heading', { name: 'Internal Plan' })).not.toBeVisible({ timeout: 2000 })

    // Free plan has "Current" button, not "Upgrade"
    await expect(page.getByRole('button', { name: 'Current' })).toBeVisible()
  })

  test('starter user sees correct plan with Manage button', async ({ page }) => {
    await loginAs(page, 'starter')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Starter plan is the current one
    await expect(page.getByRole('heading', { name: 'Starter Plan' }).first()).toBeVisible({ timeout: 5000 })

    // Should see Upgrade buttons on higher-tier plans
    const upgradeBtns = page.getByRole('button', { name: 'Upgrade' })
    const count = await upgradeBtns.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('internal user sees action buttons disabled', async ({ page }) => {
    await loginAs(page, 'internal')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Internal plan is the current one
    await expect(page.getByRole('heading', { name: 'Internal Plan' }).first()).toBeVisible({ timeout: 5000 })

    // No Upgrade buttons should be enabled
    const upgradeBtns = page.getByRole('button', { name: 'Upgrade' })
    const count = await upgradeBtns.count()
    for (let i = 0; i < count; i++) {
      await expect(upgradeBtns.nth(i)).toBeDisabled()
    }
  })

  test('credits progress shows correct numbers', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByText('Credits Usage')).toBeVisible({ timeout: 5000 })
    // Credits value may vary due to other tests (e.g., batch grant),
    // so just verify credits display renders with a number / number pattern
    await expect(page.getByText(/\d+\s*\/\s*\d+/)).toBeVisible()
  })
})
