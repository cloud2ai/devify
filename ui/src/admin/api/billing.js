import apiClient from '@/api/index'

function extractData(res) {
  const body = res?.data
  if (body && typeof body === 'object' && 'data' in body) return body.data
  return body ?? res
}

export const billingAdminApi = {
  getOverview() {
    return apiClient.get('/v1/admin/billing/overview').then(extractData)
  },

  getConfig() {
    return apiClient.get('/v1/admin/billing/config').then(extractData)
  },

  updateConfig(body) {
    return apiClient.put('/v1/admin/billing/config', body).then(extractData)
  },

  getUsers(params = {}) {
    return apiClient
      .get('/v1/admin/billing/users', { params })
      .then(extractData)
  },

  getIdentityConflicts() {
    return apiClient
      .get('/v1/admin/billing/identity-conflicts')
      .then(extractData)
  },

  grantCredits(userId, body) {
    return apiClient
      .post(`/v1/admin/billing/users/${userId}/grant`, body)
      .then(extractData)
  },

  assignPlan(userId, body) {
    return apiClient
      .post(`/v1/admin/billing/users/${userId}/assign-plan`, body)
      .then(extractData)
  },

  assignFreePlan(userId) {
    return apiClient
      .post(`/v1/admin/billing/users/${userId}/assign-free-plan`)
      .then(extractData)
  },

  syncUserFromStripe(userId) {
    return apiClient
      .post(`/v1/admin/billing/users/${userId}/sync-stripe`)
      .then(extractData)
  },

  runPaymentCheck(body = {}) {
    return apiClient
      .post('/v1/admin/billing/payment-check', body)
      .then(extractData)
  },

  runPaymentRecordBackfill(body = {}) {
    return apiClient
      .post('/v1/admin/billing/payments/backfill', body)
      .then(extractData)
  },

  batchGrantCredits(body) {
    return apiClient
      .post('/v1/admin/billing/users/batch-grant', body)
      .then(extractData)
  },

  getTransactions(params = {}) {
    return apiClient
      .get('/v1/admin/billing/transactions', { params })
      .then(extractData)
  },

  getAuditLogs(params = {}) {
    return apiClient
      .get('/v1/admin/billing/audit-logs', { params })
      .then(extractData)
  },

  getPayments(params = {}) {
    return apiClient
      .get('/v1/admin/billing/payments', { params })
      .then(extractData)
  },

  getSubscriptions(params = {}) {
    return apiClient
      .get('/v1/admin/billing/subscriptions', { params })
      .then(extractData)
  },

  getPlans() {
    return apiClient.get('/v1/admin/billing/plans').then(extractData)
  },

  createPlan(body) {
    return apiClient.post('/v1/admin/billing/plans', body).then(extractData)
  },

  updatePlan(planId, body) {
    return apiClient
      .put(`/v1/admin/billing/plans/${planId}`, body)
      .then(extractData)
  },

  syncPlanToStripe(planId) {
    return apiClient
      .post(`/v1/admin/billing/plans/${planId}/sync-stripe`)
      .then(extractData)
  },

  deletePlan(planId) {
    return apiClient.delete(`/v1/admin/billing/plans/${planId}`).then(extractData)
  }
}

export default billingAdminApi
