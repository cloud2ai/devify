import { describe, it, expect } from 'vitest'
import { useRelayDeliveries } from './useRelayDeliveries'

import { vi } from 'vitest'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => key
  })
}))

describe('useRelayDeliveries', () => {
  it('fills missing delivery urls from issue_url', () => {
    const { getRelayDeliveries } = useRelayDeliveries()

    const deliveries = getRelayDeliveries({
      issue_url: 'https://jira.example.com/browse/DEV-123',
      relay_deliveries: [
        {
          id: 1,
          external_id: 'DEV-123',
          external_url: ''
        }
      ]
    })

    expect(deliveries[0].external_url).toBe(
      'https://jira.example.com/browse/DEV-123'
    )
  })

  it('hides failed deliveries from display helpers', () => {
    const { getRelayDeliveries } = useRelayDeliveries()

    const deliveries = getRelayDeliveries({
      issue_url: 'https://jira.example.com/browse/DEV-123',
      relay_deliveries: [
        {
          id: 1,
          status: 'failed',
          external_id: 'DEV-123',
          external_url: 'https://jira.example.com/browse/DEV-123'
        },
        {
          id: 2,
          status: 'success',
          external_id: 'REQ-456',
          external_url: ''
        }
      ]
    })

    expect(deliveries).toHaveLength(1)
    expect(deliveries[0].external_id).toBe('REQ-456')
    expect(deliveries[0].external_url).toBe(
      'https://jira.example.com/browse/DEV-123'
    )
  })
})
