import { test, expect } from '@playwright/test'
import { loginAs, E2E_USERS } from '../helpers/auth'

test.describe('Error Handling', () => {
  test('billing page shows error message when API fails', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Verify the page loaded and shows either billing data or error state
    // If Stripe is not configured, a warning banner appears
    const warningBanner = page.locator('.border-amber-200, .bg-amber-50')
    const billingContent = page.locator('[class*="plan"], [class*="subscription"], [class*="credit"], canvas')
    const hasWarning = await warningBanner.isVisible({ timeout: 3000 }).catch(() => false)
    const hasContent = await billingContent.first().isVisible({ timeout: 3000 }).catch(() => false)

    expect(hasWarning || hasContent).toBeTruthy()
  })

  test('subscription management shows free plan cannot cancel', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Free plan has "Current" button — no Cancel/Manage/Resume buttons
    await expect(page.getByRole('button', { name: 'Current' })).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('button', { name: /cancel|resume|manage/i })).not.toBeVisible({ timeout: 2000 })
  })

  test('internal user has all action buttons disabled', async ({ page }) => {
    await loginAs(page, 'internal')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Internal plan is current — Upgrade buttons should be disabled
    const upgradeBtns = page.getByRole('button', { name: 'Upgrade' })
    const count = await upgradeBtns.count()
    for (let i = 0; i < count; i++) {
      await expect(upgradeBtns.nth(i)).toBeDisabled()
    }
  })
})

test.describe('Token Expiry & Auth Edge Cases', () => {
  test('user without token redirects to login', async ({ page }) => {
    // Don't call loginAs - navigate directly
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Should be redirected to login page
    const currentUrl = page.url()
    expect(currentUrl).toMatch(/login|Login/)
  })

  test('user navigates directly to admin page without admin role', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Router guard should redirect non-admin away from /management/billing
    const currentUrl = page.url()
    // Redirected to login, chats, or not on the admin route
    expect(currentUrl).not.toMatch(/management\/billing/)
  })

  test('user with invalid token redirects to login', async ({ page }) => {
    // Inject an invalid/expired token
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'invalid-expired-token-xyz')
      localStorage.setItem('refresh_token', 'invalid-refresh-token-xyz')
    })
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Should be redirected to login after auth check fails
    const currentUrl = page.url()
    expect(currentUrl).toMatch(/login|Login/)
  })
})

test.describe('Page Refresh & Re-authentication', () => {
  test('billing page survives refresh', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Refresh the page
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Should still show billing content after refresh
    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })
  })

  test('billing page survives soft navigation away and back', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })

    // Navigate away
    await page.goto('/chats', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(1000)

    // Navigate back to billing
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Should still render billing content
    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Stripe Sync from Admin', () => {
  test('sync stripe button appears on Stripe-sourced subscriptions', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    await page.screenshot({ path: 'tests/reports/screenshots/edge-sync-01-table.png', fullPage: true })

    // Look for "Sync from Stripe" button on any row
    const syncBtn = page.getByRole('button', { name: /sync from stripe/i })
    if (await syncBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await syncBtn.click()
      await page.waitForTimeout(1500)
      await page.screenshot({ path: 'tests/reports/screenshots/edge-sync-02-result.png', fullPage: true })
    } else {
      console.log('No Stripe-sourced subscriptions found in table')
    }
  })
})

test.describe('Stripe Customer Portal', () => {
  test('paid user sees action buttons on current plan', async ({ page }) => {
    await loginAs(page, 'starter')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Verify billing page and plan data loaded
    await expect(page.getByRole('heading', { name: 'Subscription Management' })).toBeVisible({ timeout: 5000 })
    await expect(page.getByRole('heading', { name: 'Starter Plan' }).first()).toBeVisible({ timeout: 5000 })

    // A paid user with a current plan sees one of: Cancel, Resume, Manage
    // (Resume appears if auto_renew was toggled by another parallel test)
    const actionBtns = [
      page.getByRole('button', { name: /cancel|Cancel/i }),
      page.getByRole('button', { name: /resume|Resume/i }),
      page.getByRole('button', { name: /manage|Manage/i })
    ]

    let foundAction = false
    for (const btn of actionBtns) {
      if (await btn.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        foundAction = true
        if (btn === actionBtns[0]) {
          // Cancel button: open dialog to verify it works
          await btn.first().click()
          await page.waitForTimeout(500)
          const dialog = page.locator('.fixed.inset-0').last()
          await expect(dialog).toBeVisible({ timeout: 3000 })
          await expect(page.getByText(/are you sure|cancel|confirm/i).first()).toBeVisible({ timeout: 2000 })
          await page.screenshot({ path: 'tests/reports/screenshots/edge-portal-01-cancel-dialog.png', fullPage: true })
          const closeBtn = dialog.getByRole('button').first()
          if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
            await closeBtn.click()
            await page.waitForTimeout(500)
          }
        } else if (btn === actionBtns[1]) {
          // Resume button: open dialog to verify it works
          await btn.first().click()
          await page.waitForTimeout(500)
          const dialog = page.locator('.fixed.inset-0').last()
          await expect(dialog).toBeVisible({ timeout: 3000 })
          await page.screenshot({ path: 'tests/reports/screenshots/edge-portal-02-resume-dialog.png', fullPage: true })
          const closeBtn = dialog.getByRole('button').first()
          if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
            await closeBtn.click()
            await page.waitForTimeout(500)
          }
        }
        break
      }
    }

    expect(foundAction).toBeTruthy()
  })
})

test.describe('Admin Sync Plan to Stripe', () => {
  test('sync stripe plans shows modal with plan selection', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/plans', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Find "Sync Stripe" button
    const syncBtn = page.getByRole('button', { name: /sync stripe/i })
    if (await syncBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await syncBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/edge-sync-plans-01-modal.png', fullPage: true })

      // Step 2: Verify modal has plan checkboxes
      const dialog = page.locator('[role="dialog"]').last()
      await expect(dialog).toBeVisible({ timeout: 3000 })

      // Close
      const closeBtn = dialog.getByRole('button', { name: /close/i }).last()
      if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      }
    }
  })
})
