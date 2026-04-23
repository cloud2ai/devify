import apiClient from './index'

export const billingApi = {
  getPlans() {
    return apiClient.get('/billing/plans')
  },

  getCurrentSubscription() {
    return apiClient.get('/billing/subscriptions/me').catch((error) => {
      if (error?.response?.status === 404) {
        return { data: null }
      }
      throw error
    })
  },

  getUserCredits() {
    return apiClient.get('/billing/credits/me')
  },

  getUsageStats(startDate, endDate) {
    const params = {}
    if (startDate) {
      params.start_date = startDate
    }
    if (endDate) {
      params.end_date = endDate
    }
    return apiClient.get('/billing/credits/usage_stats', { params })
  },

  getCreditUsageList(params) {
    return apiClient.get('/billing/credits/usage_list', { params })
  },

  createCheckoutSession(priceId) {
    return apiClient.post('/billing/subscriptions/create_checkout_session', {
      price_id: priceId
    })
  },

  createPortalSession() {
    return apiClient.post('/billing/subscriptions/create_portal_session')
  },

  cancelSubscription(subscriptionId) {
    return apiClient.post(`/billing/subscriptions/${subscriptionId}/cancel`)
  },

  resumeSubscription(subscriptionId) {
    return apiClient.post(`/billing/subscriptions/${subscriptionId}/resume`)
  },

  scheduleDowngrade(stripePriceId) {
    return apiClient.post('/billing/subscriptions/schedule-downgrade', {
      stripe_price_id: stripePriceId
    })
  }
}

export default billingApi
