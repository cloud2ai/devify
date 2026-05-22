import { Page, expect } from '@playwright/test'

export async function navigateToBilling(page: Page): Promise<void> {
  await page.goto('/billing', { waitUntil: 'domcontentloaded' })
  // Wait for the billing page shell to render (avoids networkidle which hangs on Vite HMR)
  await page.waitForTimeout(2000)
}

export async function waitForBillingData(page: Page): Promise<void> {
  // Wait for any billing section to appear on the page
  // Uses a broad selector that matches billing-related content
  try {
    await page.waitForSelector(
      '[class*="billing"], [class*="plan"], [class*="subscription"], [class*="credit"], canvas',
      { timeout: 10_000 }
    )
  } catch {
    // If no billing content shows up, take a screenshot for debugging
    console.log('Billing content did not load — page may show empty state')
  }
  await page.waitForTimeout(500)
}

export async function expectSuccessBanner(page: Page): Promise<void> {
  // Check page URL first — most reliable indicator
  if (page.url().includes('success=true')) return

  // Success banner auto-hides after 5s. Check quickly for the green banner class.
  const banner = page.locator('.bg-green-50, .border-green-200, [class*="success"]').first()
  try {
    await expect(banner).toBeVisible({ timeout: 5_000 })
    return
  } catch { /* fall through */ }

  // Check body text for success message
  const hasSuccess = await page.evaluate(() => {
    return document.body.innerText.includes('successful') ||
           document.body.innerText.includes('Payment successful')
  }).catch(() => false)
  if (hasSuccess) return

  throw new Error('No success indicator found on billing page. URL: ' + page.url())
}

export async function expectErrorBanner(page: Page): Promise<void> {
  const banner = page.locator('.border-red-200, [class*="error"]').first()
  await expect(banner).toBeVisible({ timeout: 5_000 })
}

export function getPlanCards(page: Page) {
  return page.locator('[data-testid="plan-card"], .plan-card, [class*="plan"]').filter({
    has: page.locator('h3, h4, .plan-name')
  })
}

export function getCurrentSubscriptionCard(page: Page) {
  return page.locator('[data-testid="current-subscription"], .current-subscription')
}

export function getCreditProgressBar(page: Page) {
  return page.locator('[role="progressbar"], .progress-bar, [class*="progress"]')
}

export function getUsageChart(page: Page) {
  return page.locator('canvas, [data-testid="usage-chart"]')
}

export function getCreditUsageList(page: Page) {
  return page.locator('[data-testid="credit-usage-list"], .credit-usage-list')
}

export async function waitForStripeRedirect(page: Page): Promise<void> {
  // Stripe pages use hash-based routing and heavy resources that prevent 'load'
  // from ever firing. Poll the URL instead of using waitForURL.
  for (let i = 0; i < 40; i++) {
    if (page.url().includes('checkout.stripe.com')) return
    await page.waitForTimeout(500)
  }
  throw new Error('Timed out waiting for Stripe Checkout redirect. Current URL: ' + page.url())
}

export interface StripeCheckoutDetails {
  cardNumber: string
  expiry: string
  cvc: string
  name: string
}

export const STRIPE_TEST_CARDS = {
  success: {
    cardNumber: '4242424242424242',
    expiry: '1234',
    cvc: '123',
    name: 'E2E Test User'
  },
  decline: {
    cardNumber: '4000000000000002',
    expiry: '1234',
    cvc: '123',
    name: 'E2E Test User'
  },
  threeDSecure: {
    cardNumber: '4000000000003220',
    expiry: '1234',
    cvc: '123',
    name: 'E2E Test User'
  }
}

export async function fillStripeCheckout(
  page: Page,
  card: StripeCheckoutDetails = STRIPE_TEST_CARDS.success
): Promise<void> {
  // Stripe Checkout renders form fields via JS — wait for cardNumber input to appear
  // (test mode Stripe takes ~8-12s to fully render)
  await page.waitForSelector('#cardNumber', { timeout: 20_000 })
  await page.waitForTimeout(500)

  await page.locator('#cardNumber').fill(card.cardNumber)
  await page.locator('#cardExpiry').fill(card.expiry)
  await page.locator('#cardCvc').fill(card.cvc)
  await page.locator('#billingName').fill(card.name)
}

export async function submitStripePayment(page: Page): Promise<void> {
  const payButton = page.locator(
    'button[type="submit"], button:has-text("Pay"), button:has-text("Subscribe"), .SubmitButton button'
  ).first()
  await payButton.click()

  // Wait for redirect back to our app (Stripe pages never fire 'load')
  for (let i = 0; i < 60; i++) {
    if (page.url().includes('/billing')) return
    await page.waitForTimeout(500)
  }
  throw new Error('Timed out waiting for redirect back to /billing. Current URL: ' + page.url())
}
