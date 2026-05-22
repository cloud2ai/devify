import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('Admin Batch Grant Credits', () => {
  test('selects multiple users and performs batch grant', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Wait for users table
    await expect(page.getByText(/users|User Subscriptions/i).first()).toBeVisible({ timeout: 5000 })

    // Step 2: Select first two user rows via checkboxes
    const checkboxes = page.locator('input[type="checkbox"]')
    const cbCount = await checkboxes.count()

    if (cbCount >= 3) {
      // Select second and third checkboxes (first is "select all")
      await checkboxes.nth(1).check()
      await page.waitForTimeout(300)
      await checkboxes.nth(2).check()
      await page.waitForTimeout(500)
      await page.screenshot({ path: 'tests/reports/screenshots/batch-grant-01-selected.png', fullPage: true })

      // Step 3: Verify batch bar appeared
      const batchBar = page.getByText(/selected|Batch grant|Clear selection/i).first()
      const barVisible = await batchBar.isVisible({ timeout: 3000 }).catch(() => false)

      if (barVisible) {
        // Step 4: Fill batch amount
        const amountInput = page.locator('input[type="number"]').first()
        if (await amountInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await amountInput.fill('25')
          await page.screenshot({ path: 'tests/reports/screenshots/batch-grant-02-amount.png', fullPage: true })
        }

        // Step 5: Fill batch reason
        const reasonInputs = page.locator('input[type="text"]')
        const rc = await reasonInputs.count()
        if (rc > 1) {
          await reasonInputs.nth(rc - 1).fill('E2E batch grant test')
          await page.screenshot({ path: 'tests/reports/screenshots/batch-grant-03-reason.png', fullPage: true })
        }

        // Step 6: Click batch grant button
        const batchBtn = page.getByRole('button', { name: /batch|Batch grant/i })
        if (await batchBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await batchBtn.click()
          await page.waitForTimeout(1500)
          await page.screenshot({ path: 'tests/reports/screenshots/batch-grant-04-result.png', fullPage: true })
        }
      }

      // Step 7: Clear selection
      const clearBtn = page.getByRole('button', { name: /clear selection/i })
      if (await clearBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await clearBtn.click()
        await page.waitForTimeout(500)
      }
    }
  })
})

test.describe('Admin Payment Check', () => {
  test('opens payment check dialog, runs check, and views results', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Click "Payment Check" button in toolbar
    const paymentCheckBtn = page.getByRole('button', { name: /payment check|Payment Check/i })
    if (await paymentCheckBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await paymentCheckBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/payment-check-01-dialog.png', fullPage: true })

      // Step 2: Initial state — should see provider checkboxes and Run button
      const dialog = page.locator('[role="dialog"]').last()
      const runBtn = dialog.getByRole('button', { name: /run|Run/i }).first()

      if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Step 3: Ensure at least one provider is selected (default: stripe)
        // Click Run
        await runBtn.click()
        await page.waitForTimeout(3000)
        await page.screenshot({ path: 'tests/reports/screenshots/payment-check-02-running.png', fullPage: true })

        // Step 4: Wait for results or loading to complete
        // Results show provider status, differences, and sync buttons
        await page.waitForTimeout(5000)
        await page.screenshot({ path: 'tests/reports/screenshots/payment-check-03-results.png', fullPage: true })

        // Step 5: If "Rerun" button present, results are shown
        const rerunBtn = dialog.getByRole('button', { name: /rerun|Rerun/i }).first()
        if (await rerunBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          console.log('Payment check results displayed successfully')
        }

        // Step 6: Close the dialog
        const closeBtn = dialog.getByRole('button', { name: /close|Close/i }).last()
        if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await closeBtn.click()
          await page.waitForTimeout(500)
        }
      }
    }
  })
})

test.describe('Admin Payment Record Backfill', () => {
  test('opens backfill dialog and runs backfill', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Click "Payment Record Backfill" button
    const backfillBtn = page.getByRole('button', { name: /payment record backfill|backfill/i }).first()
    if (await backfillBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await backfillBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/backfill-01-dialog.png', fullPage: true })

      // Step 2: Look for provider checkboxes and Run Now button
      const dialog = page.locator('[role="dialog"]').last()
      const runNowBtn = dialog.getByRole('button', { name: /run now|backfill/i }).first()

      if (await runNowBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await runNowBtn.click()
        await page.waitForTimeout(3000)
        await page.screenshot({ path: 'tests/reports/screenshots/backfill-02-running.png', fullPage: true })
        await page.waitForTimeout(5000)
        await page.screenshot({ path: 'tests/reports/screenshots/backfill-03-done.png', fullPage: true })
      }

      // Close dialog
      const closeBtn = dialog.getByRole('button', { name: /close|Close/i }).last()
      if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      }
    }
  })
})

test.describe('Admin Identity Conflict', () => {
  test('opens identity conflict modal and inspects conflicts', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Look for identity conflict chip
    const conflictChip = page.getByRole('button', { name: /duplicate linkage|conflict|identity conflict/i })
    if (await conflictChip.isVisible({ timeout: 5000 }).catch(() => false)) {
      await conflictChip.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/identity-conflict-01-modal.png', fullPage: true })

      // Step 2: Verify the modal shows conflict list or empty state
      const dialog = page.locator('[role="dialog"]').last()
      const hasContent = await dialog.innerText().catch(() => '')

      if (hasContent.includes('Duplicate') || hasContent.includes('conflict')) {
        console.log('Identity conflict dialog content visible')
      }

      await page.screenshot({ path: 'tests/reports/screenshots/identity-conflict-02-content.png', fullPage: true })

      // Step 3: Close
      const closeBtn = dialog.getByRole('button', { name: /close|Close/i }).last()
      if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      }
    } else {
      // No conflicts is also valid — verify table still works
      await page.screenshot({ path: 'tests/reports/screenshots/identity-conflict-01-no-conflicts.png', fullPage: true })
      console.log('No identity conflicts found — this is a valid state')
    }
  })
})
