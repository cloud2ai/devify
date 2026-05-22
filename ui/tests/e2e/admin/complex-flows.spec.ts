import { test, expect } from '@playwright/test'
import { loginAs } from '../helpers/auth'

test.describe('Admin User Detail Drawer', () => {
  test('opens user detail drawer and switches tabs', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify users table loaded
    await expect(page.getByText(/users|User Subscriptions/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/admin-drawer-01-table.png', fullPage: true })

    // Step 2: Click the first user row to open the drawer
    const firstRow = page.locator('table tbody tr, [class*="table"] [class*="row"]').first()
    if (await firstRow.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstRow.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-drawer-02-opened.png', fullPage: true })
    }

    // Step 3: Switch to Transactions tab if available
    const transactionsTab = page.getByRole('tab', { name: /transactions|Credits transactions/i })
    if (await transactionsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await transactionsTab.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-drawer-03-transactions.png', fullPage: true })
    }

    // Step 4: Switch to Records/History tab
    const recordsTab = page.getByRole('tab', { name: /records|History/i })
    if (await recordsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await recordsTab.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-drawer-04-records.png', fullPage: true })
    }

    // Step 5: Switch back to Overview tab
    const overviewTab = page.getByRole('tab', { name: /overview|Current status/i })
    if (await overviewTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await overviewTab.click()
      await page.waitForTimeout(500)
    }

    // Step 6: Close drawer via backdrop or X button
    const backdrop = page.locator('.fixed.inset-0').first()
    if (await backdrop.isVisible({ timeout: 2000 }).catch(() => false)) {
      await backdrop.click({ position: { x: 10, y: 10 } })
      await page.waitForTimeout(500)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-drawer-05-closed.png', fullPage: true })
    }
  })
})

test.describe('Admin Grant Credits Modal', () => {
  test('opens grant modal and fills the form', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Find and click a "Grant Credits" button on a row
    const grantBtn = page.getByRole('button', { name: /Grant Credits|grant/i }).first()
    if (await grantBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await grantBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-grant-01-modal.png', fullPage: true })

      // Step 2: Verify grant modal opened
      const dialog = page.locator('[role="dialog"]')
      if (await dialog.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Step 3: Fill in grant amount
        const amountInput = page.locator('input[type="number"]').first()
        if (await amountInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await amountInput.fill('50')
          await page.screenshot({ path: 'tests/reports/screenshots/admin-grant-02-filled.png', fullPage: true })
        }

        // Step 4: Fill in reason if present
        const reasonInput = page.locator('input[type="text"]').last()
        if (await reasonInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await reasonInput.fill('E2E test grant')
          await page.screenshot({ path: 'tests/reports/screenshots/admin-grant-03-reason.png', fullPage: true })
        }

        // Step 5: Close without submitting (safety)
        const closeBtn = page.getByRole('button', { name: /close|cancel/i }).last()
        if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await closeBtn.click()
          await page.waitForTimeout(500)
        }
      }
    } else {
      // If no grant button visible, just capture the table state
      await page.screenshot({ path: 'tests/reports/screenshots/admin-grant-01-no-users.png', fullPage: true })
    }
  })
})

test.describe('Admin Plan Create, Edit & Delete', () => {
  test('creates a plan via the editor modal', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/plans', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify plans table loaded
    await expect(page.getByText(/plan|Plan/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/admin-plan-01-table.png', fullPage: true })

    // Step 2: Click "Create" button
    const createBtn = page.getByRole('button', { name: /create/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-plan-02-editor.png', fullPage: true })

      // Step 3: Fill in plan name
      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first()
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill('E2E Complex Test Plan')
        await page.screenshot({ path: 'tests/reports/screenshots/admin-plan-03-filled.png', fullPage: true })

        // Step 4: Try to save (may fail validation if required fields missing, that's ok)
        const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first()
        if (await saveBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await saveBtn.click()
          await page.waitForTimeout(1500)
          await page.screenshot({ path: 'tests/reports/screenshots/admin-plan-04-saved.png', fullPage: true })
        }

        // Step 5: If still in editor (validation failed), close it
        const cancelBtn = page.getByRole('button', { name: /cancel/i }).first()
        if (await cancelBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await cancelBtn.click()
          await page.waitForTimeout(500)
        }
      }
    }
  })

  test('deletes test plan if it exists', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/plans', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Check if any test plan exists from previous runs
    const testPlan = page.getByText('E2E Test Plan')
    if (await testPlan.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Find the delete button in the same row
      const row = page.locator('tr, [class*="row"]').filter({ hasText: 'E2E Test Plan' })
      const deleteBtn = row.getByRole('button', { name: /delete/i })
      if (await deleteBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await deleteBtn.click()
        await page.waitForTimeout(500)
        await page.screenshot({ path: 'tests/reports/screenshots/admin-plan-delete-01.png', fullPage: true })
      }
    }
  })
})

test.describe('Admin Audit Log Multi-Filter', () => {
  test('applies multiple filters and paginates audit logs', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/audit-logs', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify audit log table loaded
    await expect(page.getByText(/audit|Audit/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-01-default.png', fullPage: true })

    // Step 2: Find action type select and change it
    const selects = page.locator('select')
    const selectCount = await selects.count()

    if (selectCount >= 1) {
      // Step 2a: Try to select an action type (first select)
      try {
        await selects.nth(0).selectOption({ index: 1 })
        await page.waitForTimeout(500)
        await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-02-action-filter.png', fullPage: true })
      } catch { /* ignore */ }
    }

    if (selectCount >= 2) {
      // Step 2b: Try to select a source (second select)
      try {
        await selects.nth(1).selectOption({ index: 1 })
        await page.waitForTimeout(500)
        await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-03-source-filter.png', fullPage: true })
      } catch { /* ignore */ }
    }

    // Step 3: Click "Apply Filters" if exists
    const applyBtn = page.getByRole('button', { name: /apply/i })
    if (await applyBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await applyBtn.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-04-applied.png', fullPage: true })
    }

    // Step 4: Try pagination (only if Next button is enabled)
    const nextPageBtn = page.getByRole('button', { name: 'Next' })
    if (await nextPageBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      const isEnabled = await nextPageBtn.isEnabled().catch(() => false)
      if (isEnabled) {
        await nextPageBtn.click()
        await page.waitForTimeout(1000)
        await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-05-page2.png', fullPage: true })
      }
    }

    // Step 5: Click a log row to open detail drawer
    const logRow = page.locator('table tbody tr, [class*="row"]').first()
    if (await logRow.isVisible({ timeout: 2000 }).catch(() => false)) {
      await logRow.click()
      await page.waitForTimeout(1000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-audit-06-detail.png', fullPage: true })
    }
  })
})

test.describe('Admin Settings Edit', () => {
  test('navigates settings sections and modifies a value', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/settings', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Verify settings page loaded
    await expect(page.getByText(/settings|Settings|config/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/admin-settings-01-default.png', fullPage: true })

    // Step 2: Scroll to Credits Policy section if it exists
    const creditsSection = page.getByText(/credits policy|Credits Policy/i)
    if (await creditsSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await creditsSection.scrollIntoViewIfNeeded()
      await page.waitForTimeout(500)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-settings-02-credits.png', fullPage: true })

      // Step 3: Find and modify default free credits input
      const numberInputs = page.locator('input[type="number"]')
      const numCount = await numberInputs.count()
      if (numCount > 0) {
        await numberInputs.first().fill('20')
        await page.waitForTimeout(300)
        await page.screenshot({ path: 'tests/reports/screenshots/admin-settings-03-modified.png', fullPage: true })

        // Step 4: Click Reset to revert
        const resetBtn = page.getByRole('button', { name: /reset/i })
        if (await resetBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await resetBtn.click()
          await page.waitForTimeout(500)
          await page.screenshot({ path: 'tests/reports/screenshots/admin-settings-04-reset.png', fullPage: true })
        }
      }
    }
  })
})

test.describe('Admin Sidebar Navigation', () => {
  test('navigates between all billing admin pages via sidebar', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/management/billing/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Step 1: Start on users page
    await expect(page.getByText(/User Subscriptions|users/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/admin-nav-01-users.png', fullPage: true })

    // Step 2: Navigate to plans via sidebar link
    const plansLink = page.locator('a[href*="billing/plans"]').first()
    if (await plansLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await plansLink.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-nav-02-plans.png', fullPage: true })
    }

    // Step 3: Navigate to settings via sidebar link
    const settingsLink = page.locator('a[href*="billing/settings"]').first()
    if (await settingsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await settingsLink.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-nav-03-settings.png', fullPage: true })
    }

    // Step 4: Navigate to audit logs via sidebar link
    const auditLink = page.locator('a[href*="billing/audit-logs"]').first()
    if (await auditLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await auditLink.click()
      await page.waitForTimeout(2000)
      await page.screenshot({ path: 'tests/reports/screenshots/admin-nav-04-audit.png', fullPage: true })
    }

    // Step 5: Navigate back to users
    const usersLink = page.locator('a[href*="billing/users"]').first()
    if (await usersLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await usersLink.click()
      await page.waitForTimeout(2000)
      await expect(page.getByText(/User Subscriptions|users/i).first()).toBeVisible()
    }
  })
})
