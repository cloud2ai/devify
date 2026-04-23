/**
 * API for periodic task schedule settings.
 * Base path: /v1/admin/periodic-tasks/
 */
import api from '@/api/index'

export const periodicTasksApi = {
  getSettings() {
    return api.get('/v1/admin/periodic-tasks/')
  },

  updateSettings(data) {
    return api.patch('/v1/admin/periodic-tasks/', data)
  }
}
