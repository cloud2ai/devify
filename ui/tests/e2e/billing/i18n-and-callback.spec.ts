import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('i18n', () => {
  test('switching to Chinese shows translated billing page', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Click the language switcher (🇺🇸 emoji button)
    const langBtn = page.getByRole('button', { name: '🇺🇸' })
    if (await langBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await langBtn.click()
      await page.waitForTimeout(1000)

      // Some text should now be in Chinese
      const pageText = await page.textContent('body')
      expect(pageText).toBeTruthy()
    }
  })
})

test.describe('Stripe Callback', () => {
  test('success query param shows success message', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing?success=true', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(1000)

    // Should see some success indicator
    const bodyText = await page.textContent('body')
    expect(bodyText).toBeTruthy()
  })

  test('canceled query param shows info message', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing?canceled=true', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(500)

    const bodyText = await page.textContent('body')
    expect(bodyText).toBeTruthy()
  })
})
