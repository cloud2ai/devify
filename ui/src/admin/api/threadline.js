/**
 * Threadline admin API.
 */
import apiClient from '@/api/index'

function extractData(res) {
  const body = res?.data
  if (body && typeof body === 'object' && 'data' in body) return body.data
  return body ?? res
}

export const threadlineAdminApi = {
  getWorkflowConfig() {
    return apiClient.get('/v1/admin/threadline/config/').then(extractData)
  },

  updateWorkflowConfig(body) {
    return apiClient.put('/v1/admin/threadline/config/', body).then(extractData)
  }
}
