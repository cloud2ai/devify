import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('Credit Display', () => {
  test('usage chart renders with canvas', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByText('Usage Statistics')).toBeVisible({ timeout: 5000 })
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 5000 })
  })

  test('credit usage list shows entries', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByText('Credit Usage by Chats')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Plan Button Logic', () => {
  test('free user sees Upgrade buttons on paid plans', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Should see Upgrade buttons on paid plans
    const upgradeBtns = page.getByRole('button', { name: 'Upgrade' })
    const count = await upgradeBtns.count()
    expect(count).toBeGreaterThanOrEqual(3) // Starter, Standard, Pro
  })

  test('free plan shows Current button', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('button', { name: 'Current' })).toBeVisible()
  })
})
