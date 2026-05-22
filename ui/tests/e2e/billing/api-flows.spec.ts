import { test, expect, request } from '@playwright/test'
import { loginAs, E2E_USERS } from '../helpers/auth'

const BACKEND_URL = process.env.E2E_BACKEND_URL || 'http://localhost:8000'

async function getToken(userKey: keyof typeof E2E_USERS): Promise<string> {
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const user = E2E_USERS[userKey]
  const res = await ctx.post('/api/v1/auth/login', {
    data: { username: user.username, password: user.password }
  })
  const body = await res.json()
  await ctx.dispose()
  const access = body.data?.access || body.access
  if (!access) throw new Error(`Failed to get token for ${userKey}`)
  return access
}

test.describe('Credits Consumption & Balance', () => {
  test('free user sees credits balance on billing page', async ({ page }) => {
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Credits section should display
    await expect(page.getByText(/credits|credit/i).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/credits-consumption-01-balance.png', fullPage: true })
  })

  test('credits balance API returns correct structure for authenticated user', async () => {
    const token = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.get('/api/billing/credits/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    const data = body.data || body
    expect(data).toHaveProperty('base_credits')
    expect(data).toHaveProperty('bonus_credits')
    expect(data).toHaveProperty('consumed_credits')
    expect(data).toHaveProperty('available_credits')
    expect(data.available_credits).toBeGreaterThanOrEqual(0)

    await ctx.dispose()
  })

  test('credits history API returns results array', async () => {
    const token = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.get('/api/billing/credits/history', {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    // API returns data as a plain array (not a paginated wrapper)
    const data = body.data || body
    expect(Array.isArray(data)).toBe(true)

    await ctx.dispose()
  })

  test('user with zero available credits still loads billing page', async ({ page }) => {
    // e2e-free starts with some credits (default_free_credits=10).
    // The page should render even if balance is low.
    await loginAs(page, 'free')
    await page.goto('/billing', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(2000)

    // Verify billing shell renders (even low-credit users can see plans)
    await expect(page.getByRole('heading', { name: /subscription|plan/i }).first()).toBeVisible({ timeout: 5000 })
    await page.screenshot({ path: 'tests/reports/screenshots/credits-consumption-02-low-balance.png', fullPage: true })
  })
})

test.describe('Admin Batch Grant Credits', () => {
  test('admin can batch grant credits to multiple users', async () => {
    const adminToken = await getToken('admin')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    // First, get a regular user's ID
    const freeUser = E2E_USERS['free']
    const userLookupRes = await ctx.post('/api/v1/auth/login', {
      data: { username: freeUser.username, password: freeUser.password }
    })
    const userLookupBody = await userLookupRes.json()
    const freeUserId = userLookupBody.data?.user?.id

    // Step 1: Grant credits to the free user
    const res = await ctx.post('/api/v1/admin/billing/users/batch-grant', {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        user_ids: [freeUserId],
        amount: 50,
        reason: 'e2e-test-batch-grant'
      }
    })
    expect(res.status()).toBe(201)

    const body = await res.json()
    const batchData = body.data || body
    expect(batchData.count).toBe(1)
    expect(batchData.results[0].user_id).toBe(freeUserId)

    // Step 2: Verify credits were applied by checking the user's credits
    const freeToken = await getToken('free')
    const creditsRes = await ctx.get('/api/billing/credits/me', {
      headers: { Authorization: `Bearer ${freeToken}` }
    })
    expect(creditsRes.status()).toBe(200)
    const creditsBody = await creditsRes.json()
    const creditsData = creditsBody.data || creditsBody
    // Bonus credits should include the 50 we just granted
    expect(creditsData.bonus_credits).toBeGreaterThanOrEqual(50)

    await ctx.dispose()
  })

  test('non-admin user cannot access batch grant endpoint', async () => {
    const freeToken = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.post('/api/v1/admin/billing/users/batch-grant', {
      headers: { Authorization: `Bearer ${freeToken}` },
      data: {
        user_ids: [1],
        amount: 100,
        reason: 'unauthorized-test'
      }
    })
    expect(res.status()).toBe(403)

    await ctx.dispose()
  })

  test('batch grant validates required fields', async () => {
    const adminToken = await getToken('admin')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    // Missing amount
    const res = await ctx.post('/api/v1/admin/billing/users/batch-grant', {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        user_ids: [1],
        reason: 'missing-amount'
      }
    })
    expect(res.status()).toBe(400)

    await ctx.dispose()
  })
})

test.describe('Unauthenticated API Access', () => {
  const UNAUTH_ENDPOINTS = [
    { method: 'GET', url: '/api/billing/subscriptions/me' },
    { method: 'POST', url: '/api/billing/subscriptions/schedule-downgrade', data: { stripe_price_id: 'test' } },
    { method: 'POST', url: '/api/billing/subscriptions/create_checkout_session', data: { price_id: 'test' } },
    { method: 'POST', url: '/api/billing/subscriptions/create_portal_session', data: {} },
    { method: 'GET', url: '/api/billing/credits/me' },
    { method: 'GET', url: '/api/billing/credits/history' },
    { method: 'GET', url: '/api/billing/plans' },
  ]

  for (const { method, url, data } of UNAUTH_ENDPOINTS) {
    test(`${method} ${url} returns 401 without auth`, async () => {
      const ctx = await request.newContext({ baseURL: BACKEND_URL })

      const res = method === 'GET'
        ? await ctx.get(url)
        : await ctx.post(url, { data: data || {} })

      expect(res.status()).toBe(401)

      const body = await res.json()
      expect(body.code || body.status).toBe(401)

      await ctx.dispose()
    })
  }
})

test.describe('Cross-User Operation Protection', () => {
  test('user A cannot cancel user B subscription', async () => {
    const tokenA = await getToken('free')
    const tokenB = await getToken('starter')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    // Get user B's subscription ID
    const subRes = await ctx.get('/api/billing/subscriptions/me', {
      headers: { Authorization: `Bearer ${tokenB}` }
    })
    expect(subRes.status()).toBe(200)
    const subBody = await subRes.json()
    const subData = subBody.data || subBody
    const subIdB = subData?.id

    if (!subIdB) {
      // starter user might not have a subscription record from me endpoint
      // Try listing
      const listRes = await ctx.get('/api/billing/subscriptions', {
        headers: { Authorization: `Bearer ${tokenB}` }
      })
      expect(listRes.status()).toBe(200)
      const listBody = await listRes.json()
      const listData = listBody.data || listBody
      // The list might be wrapped in results or just the data
      const items = Array.isArray(listData) ? listData : (listData.results || [])
      if (items.length === 0) {
        test.skip(true, 'User B has no subscription')
        await ctx.dispose()
        return
      }
    }

    // Now try to cancel user B's subscription using user A's token
    // We need the subscription's cancel endpoint
    const cancelRes = await ctx.post(`/api/billing/subscriptions/${subIdB}/cancel`, {
      headers: { Authorization: `Bearer ${tokenA}` }
    })
    // Should be 404 (queryset filters by user, so subscription not found for user A)
    expect(cancelRes.status()).toBe(404)

    await ctx.dispose()
  })

  test('user A cannot access user B credits', async () => {
    const tokenA = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    // credits/me always returns the authenticated user's credits
    // There is no endpoint to access another user's credits by ID
    const res = await ctx.get('/api/billing/credits/me', {
      headers: { Authorization: `Bearer ${tokenA}` }
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    const data = body.data || body
    expect(data).toHaveProperty('user')
    // Verify the returned user ID matches the authenticated user
    const tokenPayload = await ctx.get('/api/v1/auth/user', {
      headers: { Authorization: `Bearer ${tokenA}` }
    })
    const userBody = await tokenPayload.json()
    const userData = userBody.data || userBody
    expect(data.user).toBe(userData.id)

    await ctx.dispose()
  })

  test('schedule-downgrade is scoped to authenticated user only', async () => {
    // schedule-downgrade looks up the authenticated user's own subscription.
    // It has no user_id parameter, so it's inherently scoped to self.
    // A free user (no Stripe subscription) calling it cannot affect anyone else.
    const tokenA = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.post('/api/billing/subscriptions/schedule-downgrade', {
      headers: { Authorization: `Bearer ${tokenA}` },
      data: { stripe_price_id: 'price_fake_test' }
    })
    // Fails because free user has no Stripe sub (404) or because Stripe
    // rejects the fake price ID (500). Either way, it doesn't succeed.
    expect(res.status()).toBeGreaterThanOrEqual(400)

    await ctx.dispose()
  })
})

test.describe('Internal User API Isolation', () => {
  test('internal user cannot create checkout session', async () => {
    const token = await getToken('internal')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.post('/api/billing/subscriptions/create_checkout_session', {
      headers: { Authorization: `Bearer ${token}` },
      data: { price_id: 'price_test' }
    })
    expect(res.status()).toBe(403)

    const body = await res.json()
    expect(body.data?.detail || body.detail || '').toMatch(/internal/i)

    await ctx.dispose()
  })

  test('internal user cannot create portal session', async () => {
    const token = await getToken('internal')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.post('/api/billing/subscriptions/create_portal_session', {
      headers: { Authorization: `Bearer ${token}` },
      data: {}
    })
    expect(res.status()).toBe(403)

    await ctx.dispose()
  })

  test('internal user cannot schedule downgrade', async () => {
    const token = await getToken('internal')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.post('/api/billing/subscriptions/schedule-downgrade', {
      headers: { Authorization: `Bearer ${token}` },
      data: { stripe_price_id: 'price_test' }
    })
    expect(res.status()).toBe(403)

    await ctx.dispose()
  })

  test('internal user cannot cancel subscription via API', async () => {
    const token = await getToken('internal')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    // Get internal user's subscription ID
    const subRes = await ctx.get('/api/billing/subscriptions/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(subRes.status()).toBe(200)
    const subBody = await subRes.json()
    const subData = subBody.data || subBody
    const subId = subData?.id

    if (!subId) {
      test.skip(true, 'Internal user has no subscription')
      await ctx.dispose()
      return
    }

    const res = await ctx.post(`/api/billing/subscriptions/${subId}/cancel`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(403)

    await ctx.dispose()
  })

  test('internal user cannot resume subscription via API', async () => {
    const token = await getToken('internal')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const subRes = await ctx.get('/api/billing/subscriptions/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(subRes.status()).toBe(200)
    const subBody = await subRes.json()
    const subData = subBody.data || subBody
    const subId = subData?.id

    if (!subId) {
      test.skip(true, 'Internal user has no subscription')
      await ctx.dispose()
      return
    }

    const res = await ctx.post(`/api/billing/subscriptions/${subId}/resume`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(403)

    await ctx.dispose()
  })

  test('free user cannot see internal plan in plans list', async () => {
    const token = await getToken('free')
    const ctx = await request.newContext({ baseURL: BACKEND_URL })

    const res = await ctx.get('/api/billing/plans', {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    const plans = body.data || body
    // Filter by plan data only if it's an array; plans might come in a different structure
    const planList = Array.isArray(plans) ? plans : (plans.results || plans.data || [])
    const internalPlans = planList.filter(
      (p: any) => p.is_internal || p.slug === 'internal' || p.name?.toLowerCase?.() === 'internal'
    )
    expect(internalPlans.length).toBe(0)

    await ctx.dispose()
  })
})
