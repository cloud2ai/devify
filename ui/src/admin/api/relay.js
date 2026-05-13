/**
 * Relay admin API.
 */
import apiClient from '@/api/index'

function extractData(res) {
  const body = res?.data
  if (body && typeof body === 'object' && 'data' in body) return body.data
  return body ?? res
}

export const relayAdminApi = {
  getRelayConfig() {
    return apiClient.get('/v1/admin/apps/relay/config').then(extractData)
  },

  updateRelayConfig(body) {
    return apiClient.put('/v1/admin/apps/relay/config', body).then(extractData)
  }
}
