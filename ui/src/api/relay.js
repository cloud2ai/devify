import apiClient from './index'

function extractData(response) {
  const payload = response?.data
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return payload.data
  }
  return payload ?? response
}

export const relayApi = {
  getApps() {
    return apiClient.get('/v1/apps').then(extractData)
  },

  getSubscriptions() {
    return apiClient.get('/v1/apps/relay/subscriptions').then(extractData)
  },

  createSubscription(payload) {
    return apiClient
      .post('/v1/apps/relay/subscriptions', payload)
      .then(extractData)
  },

  updateSubscription(id, payload) {
    return apiClient
      .patch(`/v1/apps/relay/subscriptions/${id}`, payload)
      .then(extractData)
  },

  deleteSubscription(id) {
    return apiClient
      .delete(`/v1/apps/relay/subscriptions/${id}`)
      .then(extractData)
  },

  testSubscription(payload) {
    return apiClient.post('/v1/apps/relay/test', payload).then(extractData)
  },

  getEvents(params = {}) {
    return apiClient.get('/v1/apps/relay/events', { params }).then(extractData)
  },

  getEvent(id) {
    return apiClient.get(`/v1/apps/relay/events/${id}`).then(extractData)
  },

  getDeliveries(params = {}) {
    return apiClient
      .get('/v1/apps/relay/deliveries', { params })
      .then(extractData)
  },

  getDelivery(id) {
    return apiClient.get(`/v1/apps/relay/deliveries/${id}`).then(extractData)
  },

  retryEvent(id) {
    return apiClient.post(`/v1/apps/relay/events/${id}/retry`).then(extractData)
  },

  retryDelivery(id) {
    return apiClient
      .post(`/v1/apps/relay/deliveries/${id}/retry`)
      .then(extractData)
  }
}
