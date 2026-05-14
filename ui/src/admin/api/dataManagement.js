/**
 * Admin data management API.
 */
import apiClient from '@/api/index'
import { extractResponseData } from '@/utils/api'

export const dataManagementApi = {
  getConversations(params = {}) {
    return apiClient
      .get('/v1/admin/threadline/conversations/', { params })
      .then(extractResponseData)
  },

  getConversation(uuid) {
    return apiClient
      .get(`/v1/admin/threadline/conversations/${uuid}/`)
      .then(extractResponseData)
  },

  getConversationTasks(uuid, params = {}) {
    return apiClient
      .get(`/v1/admin/threadline/conversations/${uuid}/tasks/`, { params })
      .then(extractResponseData)
  },

  getConversationTask(uuid, taskPk) {
    return apiClient
      .get(`/v1/admin/threadline/conversations/${uuid}/tasks/${taskPk}/`)
      .then(extractResponseData)
  }
}
