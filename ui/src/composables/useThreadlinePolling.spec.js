import { describe, it, expect, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { useThreadlinePolling } from './useThreadlinePolling'

vi.mock('@/api/chat', () => ({
  chatApi: {
    getThreadline: vi.fn(),
    retryThreadline: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showError: vi.fn()
  })
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => key
  })
}))

describe('useThreadlinePolling', () => {
  it('resets retry state when requested', async () => {
    const threadline = ref(null)
    const route = { params: { id: 'thread-1' } }
    const polling = useThreadlinePolling(threadline, route)

    polling.retrying.value = true
    polling.showRetryDialog.value = true
    polling.retryStartedAt.value = Date.now()

    polling.resetRetryState()
    await nextTick()

    expect(polling.retrying.value).toBe(false)
    expect(polling.showRetryDialog.value).toBe(false)
    expect(polling.retryStartedAt.value).toBe(null)
  })
})
