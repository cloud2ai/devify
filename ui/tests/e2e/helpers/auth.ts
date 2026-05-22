import { Page, request } from '@playwright/test'

export interface TestUser {
  email: string
  password: string
  username: string
  plan: 'free' | 'starter' | 'standard' | 'pro' | 'internal'
  isAdmin?: boolean
}

const BACKEND_URL = process.env.E2E_BACKEND_URL || 'http://localhost:8000'

export const E2E_USERS: Record<string, TestUser> = {
  free: {
    email: 'e2e-free@devify.test',
    username: 'e2e-free',
    password: 'e2e-test-password',
    plan: 'free'
  },
  starter: {
    email: 'e2e-starter@devify.test',
    username: 'e2e-starter',
    password: 'e2e-test-password',
    plan: 'starter'
  },
  admin: {
    email: 'e2e-admin@devify.test',
    username: 'e2e-admin',
    password: 'e2e-test-password',
    plan: 'free',
    isAdmin: true
  },
  standard: {
    email: 'e2e-standard@devify.test',
    username: 'e2e-standard',
    password: 'e2e-test-password',
    plan: 'standard'
  },
  pro: {
    email: 'e2e-pro@devify.test',
    username: 'e2e-pro',
    password: 'e2e-test-password',
    plan: 'pro'
  },
  internal: {
    email: 'e2e-internal@devify.test',
    username: 'e2e-internal',
    password: 'e2e-test-password',
    plan: 'internal'
  }
}

export async function loginAs(page: Page, userKey: keyof typeof E2E_USERS): Promise<void> {
  const user = E2E_USERS[userKey]

  // Get token via API
  const ctx = await request.newContext({ baseURL: BACKEND_URL })
  const res = await ctx.post('/api/v1/auth/login', {
    data: { username: user.username, password: user.password }
  })
  const body = await res.json()
  await ctx.dispose()

  const access = body.data?.access || body.access
  const refresh = body.data?.refresh || body.refresh

  if (!access) {
    throw new Error(`Failed to get token for ${userKey}: ${JSON.stringify(body)}`)
  }

  // Set token in localStorage before any navigation
  await page.addInitScript(
    ({ access, refresh }) => {
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)
    },
    { access, refresh }
  )
}
