/**
 * Management portal API (admin-only): user list, etc.
 */
import apiClient from '@/api/index'

function extractData(res) {
  const body = res?.data
  if (body && typeof body === 'object' && 'data' in body) return body.data
  return body ?? res
}

export const managementApi = {
  getUsers(params = {}) {
    return apiClient.get('/v1/management/users/', { params }).then(extractData)
  },

  createUser(body) {
    return apiClient.post('/v1/management/users/', body).then(extractData)
  },

  getGroups(params = {}) {
    return apiClient.get('/v1/management/groups/', { params }).then(extractData)
  },

  createGroup(body) {
    return apiClient.post('/v1/management/groups/', body).then(extractData)
  }
}
