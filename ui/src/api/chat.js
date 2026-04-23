import api from './index'

export const chatApi = {
  // Get threadlines (email messages with attachments)
  getThreadlines(params = {}) {
    return api.get('/v1/threadlines', { params })
  },

  // Get specific threadline by ID
  getThreadline(id) {
    return api.get(`/v1/threadlines/${id}`)
  },

  // Create new threadline
  createThreadline(data) {
    return api.post('/v1/threadlines', data)
  },

  // Update threadline
  updateThreadline(id, data) {
    return api.patch(`/v1/threadlines/${id}`, data)
  },

  // Delete threadline
  deleteThreadline(id) {
    return api.delete(`/v1/threadlines/${id}`)
  },

  // Search threadlines
  searchThreadlines(query, params = {}) {
    return api.get('/v1/threadlines', {
      params: {
        search: query,
        ...params
      }
    })
  },

  // Filter threadlines by status
  filterByStatus(status, params = {}) {
    return api.get('/v1/threadlines', {
      params: {
        status,
        ...params
      }
    })
  },

  // Get threadlines by task ID
  getByTaskId(taskId, params = {}) {
    return api.get('/v1/threadlines', {
      params: {
        task_id: taskId,
        ...params
      }
    })
  },

  // Export threadline data
  exportThreadline(id, format = 'json') {
    return api.get(`/v1/threadlines/${id}/export`, {
      params: { format },
      responseType: 'blob'
    })
  },

  // Retry threadline processing
  retryThreadline(id, options = {}) {
    return api.post(`/v1/threadlines/${id}/retry`, {
      language: options.language,
      scene: options.scene,
      force: options.force || false
    })
  },

  // Create or refresh share link for a threadline
  createShareLink(id, data) {
    return api.post(`/v1/threadlines/${id}/share-link`, data)
  },

  // Get share link details for the owner
  getShareLink(token) {
    return api.get(`/v1/share-links/${token}`)
  },

  // Delete (deactivate) share link
  deleteShareLink(token) {
    return api.delete(`/v1/share-links/${token}`)
  },

  // Public share metadata or content
  getPublicShare(token) {
    return api.get(`/v1/public/share/${token}`)
  },

  // Verify password for public share
  verifyPublicShare(token, data) {
    return api.post(`/v1/public/share/${token}/verify`, data)
  }
}
