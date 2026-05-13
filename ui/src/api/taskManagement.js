import api from '@/api/index'

function extractData(response) {
  const payload = response?.data
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return payload.data
  }
  return payload ?? response
}

export const taskManagementApi = {
  getExecutionByTaskId(taskId, params = {}) {
    return api
      .get(`/v1/tasks/executions/by-task-id/${taskId}/`, {
        params: { my_tasks: 'false', ...params }
      })
      .then(extractData)
  }
}
