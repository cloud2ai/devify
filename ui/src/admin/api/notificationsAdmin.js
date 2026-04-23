/**
 * Notifications admin API (agentcore-notifier: stats, records, channels, global).
 * Base path: /v1/admin/notifications/
 * Webhook/email config is via channels API only.
 */
import apiClient from '@/api/index'
import { extractResponseData } from '@/utils/api'

export const notificationsAdminApi = {
  getStats(params = {}) {
    return apiClient
      .get('/v1/admin/notifications/notification-stats/', { params })
      .then(extractResponseData)
  },
  getRecords(params = {}) {
    return apiClient
      .get('/v1/admin/notifications/notification-records/', { params })
      .then(extractResponseData)
  },
  getRecord(uuid) {
    return apiClient
      .get(`/v1/admin/notifications/notification-records/${uuid}/`)
      .then(extractResponseData)
  },
  /**
   * List users that have at least one notification record (for stats/records scope dropdown).
   * Returns [{ user_id, display }].
   */
  getUsers() {
    return apiClient
      .get('/v1/admin/notifications/users/')
      .then(extractResponseData)
  },
  getGlobalConfig() {
    return apiClient
      .get('/v1/admin/notifications/global/')
      .then(extractResponseData)
  },
  putGlobalConfig(value) {
    return apiClient
      .put('/v1/admin/notifications/global/', { value })
      .then(extractResponseData)
  },
  getChannels(params = {}) {
    return apiClient
      .get('/v1/admin/notifications/channels/', { params })
      .then(extractResponseData)
  },
  postChannel(body) {
    return apiClient
      .post('/v1/admin/notifications/channels/', body)
      .then(extractResponseData)
  },
  getChannel(id) {
    return apiClient
      .get(`/v1/admin/notifications/channels/${id}/`)
      .then(extractResponseData)
  },
  putChannel(id, body) {
    return apiClient
      .put(`/v1/admin/notifications/channels/${id}/`, body)
      .then(extractResponseData)
  },
  deleteChannel(id) {
    return apiClient.delete(`/v1/admin/notifications/channels/${id}/`)
  },
  /**
   * Validate channel config (webhook: send test message; email: SMTP connect).
   * Body: { channel_type: 'webhook'|'email', config: { ... } }
   */
  validateChannel(body) {
    return apiClient
      .post('/v1/admin/notifications/channels/validate/', body)
      .then(extractResponseData)
      .catch((err) => {
        const data = err.response?.data
        const inner = typeof data === 'object' && data?.data
        let message =
          (typeof inner === 'object' && (inner?.error ?? inner?.detail)) ??
          (typeof data === 'object' && (data?.error ?? data?.detail)) ??
          err.message
        if (Array.isArray(message)) message = message.join('; ')
        if (typeof message !== 'string') message = ''
        if (message === 'Request failed with status code 400') message = ''
        throw new Error(message)
      })
  }
}
