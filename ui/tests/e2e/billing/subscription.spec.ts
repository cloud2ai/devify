import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('Subscription Management', () => {
  test('free user cannot cancel free plan', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Free plan should just have "Current" button, no cancel option
    const currentBtn = page.getByRole('button', { name: 'Current' })
    await expect(currentBtn).toBeVisible()
    // No Cancel, Manage, or Resume buttons for free plan
    await expect(page.getByRole('button', { name: /cancel|resume|manage/i })).not.toBeVisible({ timeout: 2000 })
  })
})
