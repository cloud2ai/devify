/**
 * API for agentcore-task: task executions list, stats, retrieve, sync, config.
 * Base path: /v1/tasks/
 */
import api from '@/api/index'

export const taskManagementApi = {
  getExecutions(params = {}) {
    return api.get('/v1/tasks/executions/', { params })
  },

  getExecution(id, params = {}) {
    const query = { my_tasks: 'false', ...params }
    return api.get(`/v1/tasks/executions/${id}/`, { params: query })
  },

  syncExecution(id) {
    return api.post(`/v1/tasks/executions/${id}/sync/`, null, {
      params: { my_tasks: 'false' }
    })
  },

  getStats(params = {}) {
    return api.get('/v1/tasks/executions/stats/', { params })
  },

  getConfig() {
    return api.get('/v1/tasks/config/')
  },

  updateConfig(data) {
    return api.patch('/v1/tasks/config/', data)
  }
}
