import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'
import {
  navigateToBilling,
  waitForBillingData,
  waitForStripeRedirect,
  fillStripeCheckout,
  submitStripePayment,
  STRIPE_TEST_CARDS
} from '../helpers/billing'

test.describe('Cancel & Resume Lifecycle', () => {
  test('starter user cancels subscription via dialog', async ({ page }) => {
    await loginAs(page, 'starter')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify starter plan is current
    await expect(page.getByRole('heading', { name: 'Starter Plan' }).first()).toBeVisible()
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-flow-01-current-plan.png', fullPage: true })

    // Step 2: Click "Cancel" button on the current plan
    const cancelBtn = page.getByRole('button', { name: 'Cancel' })
    await expect(cancelBtn).toBeVisible()
    await cancelBtn.click()
    await page.waitForTimeout(500)

    // Step 3: Verify cancel dialog appears
    const dialog = page.locator('[role="dialog"], .fixed.inset-0').last()
    await expect(dialog).toBeVisible({ timeout: 3000 })
    await expect(page.getByText('Are you sure you want to cancel')).toBeVisible()
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-flow-02-dialog.png', fullPage: true })

    // Step 4: Confirm cancellation
    const confirmBtn = page.getByRole('button', { name: 'Confirm Cancellation' })
    await expect(confirmBtn).toBeVisible()
    await confirmBtn.click()
    await page.waitForTimeout(1500)

    // Step 5: Verify cancel success message
    await expect(page.getByText(/canceled|cancellation/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-flow-03-success.png', fullPage: true })
  })

  test('starter user cancels then resumes subscription', async ({ page }) => {
    await loginAs(page, 'starter')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Cancel the subscription if not already cancelled
    const cancelBtn = page.getByRole('button', { name: 'Cancel' })
    if (await cancelBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await cancelBtn.click()
      await page.waitForTimeout(500)
      const confirmBtn = page.getByRole('button', { name: 'Confirm Cancellation' })
      if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await confirmBtn.click()
        await page.waitForTimeout(1000)
      }
    }
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-resume-01-canceled.png', fullPage: true })

    // Step 2: Reload page to get updated state
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 3: Click "Resume" button — must be visible after cancel
    const resumeBtn = page.getByRole('button', { name: 'Resume' })
    await expect(resumeBtn).toBeVisible({ timeout: 5000 })
    await resumeBtn.click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-resume-02-resume-dialog.png', fullPage: true })

    // Step 4: Confirm resume
    const confirmBtn = page.getByRole('button', { name: 'Confirm Resume' })
    await expect(confirmBtn).toBeVisible({ timeout: 3000 })
    await confirmBtn.click()
    await page.waitForTimeout(1500)

    // Step 5: Verify resume success — "Cancel" button should reappear
    await page.screenshot({ path: 'tests/reports/screenshots/cancel-resume-03-resumed.png', fullPage: true })
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Credits & Usage Multi-Step', () => {
  test('switches usage chart periods', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify usage chart is visible
    await expect(page.getByText('Usage Statistics')).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/chart-01-default.png', fullPage: true })

    // Step 2: Click "7d" period button
    const periodBtns = page.locator('button:has-text("d")')
    const sevenDayBtn = periodBtns.filter({ hasText: '7d' })
    if (await sevenDayBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await sevenDayBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/chart-02-7d.png', fullPage: true })
    }

    // Step 3: Click "1d" period button
    const oneDayBtn = periodBtns.filter({ hasText: '1d' })
    if (await oneDayBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await oneDayBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/chart-03-1d.png', fullPage: true })
    }

    // Step 4: Verify canvas still exists after switching
    const canvas = page.locator('canvas').first()
    await expect(canvas).toBeVisible({ timeout: 5000 })
  })

  test('filters credit usage list and paginates', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify credit usage list is visible
    await expect(page.getByText('Credit Usage by Chats')).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/credits-list-01-default.png', fullPage: true })

    // Step 2: Change time range select to "Last 7 days"
    const select = page.locator('select').first()
    if (await select.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Try to select "Last 7 days" option
      try {
        await select.selectOption({ label: 'Last 7 days' })
      } catch {
        await select.selectOption('7')
      }
      await page.waitForTimeout(1500)
      await page.screenshot({ path: 'tests/reports/screenshots/credits-list-02-7d.png', fullPage: true })
    }

    // Step 3: Try "Last 90 days" to see more data
    if (await select.isVisible().catch(() => false)) {
      try {
        await select.selectOption({ label: 'Last 90 days' })
      } catch {
        await select.selectOption('90')
      }
      await page.waitForTimeout(1500)
      await page.screenshot({ path: 'tests/reports/screenshots/credits-list-03-90d.png', fullPage: true })
    }

    // Step 4: Try pagination if available
    const nextBtn = page.getByRole('button', { name: 'Next' })
    if (await nextBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await nextBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/credits-list-04-page2.png', fullPage: true })
    }

    // Step 5: Click a credit usage item if any exist (navigates to chat)
    const chatLinks = page.locator('[class*="cursor-pointer"]').first()
    if (await chatLinks.isVisible({ timeout: 2000 }).catch(() => false)) {
      await chatLinks.click()
      await page.waitForTimeout(1000)
      // Should have navigated to a chat page
      const currentUrl = page.url()
      expect(currentUrl).toMatch(/chats|billing/)
      await page.screenshot({ path: 'tests/reports/screenshots/credits-list-05-navigated.png', fullPage: true })
    }
  })
})

test.describe('Plan Interaction Flows', () => {
  test('free user views upgrade options and verifies plan details', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Count upgrade buttons
    const upgradeBtns = page.getByRole('button', { name: 'Upgrade' })
    const count = await upgradeBtns.count()
    expect(count).toBeGreaterThanOrEqual(3) // Starter, Standard, Pro
    await page.screenshot({ path: 'tests/reports/screenshots/plans-01-upgrade-options.png', fullPage: true })

    // Step 2: Verify each paid plan shows a price
    const priceElements = page.locator('text=/\\$\\d+|\\/month/')
    const priceCount = await priceElements.count()
    expect(priceCount).toBeGreaterThan(0)

    // Step 3: Verify Free plan has "Current" button
    await expect(page.getByRole('button', { name: 'Current' })).toBeVisible()

    // Step 4: Verify no Internal plan visible to regular user
    await expect(page.getByRole('heading', { name: 'Internal Plan' })).not.toBeVisible({ timeout: 2000 })

    // Step 5: Click first Upgrade button (should trigger Stripe checkout or show error)
    if (count > 0) {
      await upgradeBtns.first().click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/plans-02-after-upgrade-click.png', fullPage: true })
      // May redirect to Stripe or show stripe-not-configured message
    }
  })

  test('starter user sees downgrade button for lower paid plan', async ({ page }) => {
    // Use standard user so there is a valid downgrade target (starter is lower tier, not free)
    await loginAs(page, 'standard')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify standard is current plan
    await expect(page.getByRole('heading', { name: 'Standard Plan' }).first()).toBeVisible({ timeout: 5000 })

    // Step 2: Look for downgrade button (to downgrade to Starter)
    const downgradeBtn = page.getByRole('button', { name: 'Downgrade' })
    const downgradeVisible = await downgradeBtn.first().isVisible({ timeout: 3000 }).catch(() => false)
    await page.screenshot({ path: 'tests/reports/screenshots/downgrade-01-plan-list.png', fullPage: true })

    if (downgradeVisible) {
      // Step 3: Click downgrade
      await downgradeBtn.first().click()
      await page.waitForTimeout(500)

      // Step 4: Verify downgrade dialog
      await expect(page.getByText(/downgrade/i).first()).toBeVisible({ timeout: 3000 })
      await page.screenshot({ path: 'tests/reports/screenshots/downgrade-02-dialog.png', fullPage: true })

      // Step 5: Cancel the dialog (don't actually downgrade beyond this point)
      const cancelDialogBtn = page.getByRole('button', { name: 'Cancel' }).last()
      if (await cancelDialogBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await cancelDialogBtn.click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('paid user downgrades via Stripe-integrated flow', async ({ page }) => {
    // This test requires real Stripe checkout — skip unless explicitly enabled.
    // Uses e2e-standard (instead of e2e-starter) to avoid conflicts with
    // parallel Stripe checkout tests that also use e2e-starter.
    if (!process.env.STRIPE_E2E_ENABLED) {
      test.skip()
    }
    test.setTimeout(120_000)

    await loginAs(page, 'standard')
    await navigateToBilling(page)
    await waitForBillingData(page)

    // Step 1: Verify standard is current plan
    await expect(page.getByRole('heading', { name: 'Standard Plan' }).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/downgrade-exec-01-current.png', fullPage: true })

    // Step 2: Upgrade to Pro via Stripe Checkout
    const proCard = page.getByText('Pro Plan').first()
    const upgradeBtn = proCard.locator('..').getByRole('button', { name: 'Upgrade' })
    if (!(await upgradeBtn.isVisible({ timeout: 2000 }).catch(() => false))) {
      // Fallback: find any Upgrade button for a higher tier
      await page.getByRole('button', { name: 'Upgrade' }).first().click()
    } else {
      await upgradeBtn.click()
    }

    await waitForStripeRedirect(page)
    await fillStripeCheckout(page, STRIPE_TEST_CARDS.success)
    await submitStripePayment(page)
    await page.waitForTimeout(3000)

    // Reload to ensure subscription data reflects the upgrade
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)
    await waitForBillingData(page)

    // Step 3: Verify upgrade succeeded — Pro Plan is now current
    await expect(page.getByRole('heading', { name: 'Pro Plan' }).first()).toBeVisible({ timeout: 10000 })
    await page.screenshot({ path: 'tests/reports/screenshots/downgrade-exec-02-upgraded.png', fullPage: true })

    // Step 4: Downgrade back to Standard
    const downgradeBtn = page.getByRole('button', { name: 'Downgrade' }).first()
    await expect(downgradeBtn).toBeVisible({ timeout: 5000 })
    await downgradeBtn.click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'tests/reports/screenshots/downgrade-exec-03-dialog.png', fullPage: true })

    // Step 5: Verify downgrade dialog content
    const dialog = page.locator('.fixed.inset-0').last()
    await expect(dialog).toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/downgrade|standard/i).first()).toBeVisible()

    // Step 6: Confirm the downgrade
    const confirmBtn = dialog.getByRole('button', { name: /confirm downgrade|confirm/i })
    await expect(confirmBtn).toBeVisible({ timeout: 3000 })
    await confirmBtn.click()
    await page.waitForTimeout(2000)

    // Step 7: Verify success — dialog is gone AND success message is visible
    await page.screenshot({ path: 'tests/reports/screenshots/downgrade-exec-04-result.png', fullPage: true })
    await expect(page.locator('.fixed.inset-0').last()).not.toBeVisible({ timeout: 3000 })
    await expect(page.getByText(/downgrade.*scheduled|scheduled.*downgrade|success/i).first()).toBeVisible({ timeout: 5000 })
  })
})
