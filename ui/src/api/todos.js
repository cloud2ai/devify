import api from './index'

export const todosApi = {
  // Get TODO list with filtering, pagination, search, ordering
  getTodos(params = {}) {
    return api.get('/v1/todos', { params })
  },

  // Get specific TODO by ID
  getTodo(id) {
    return api.get(`/v1/todos/${id}`)
  },

  // Create new TODO
  createTodo(data) {
    return api.post('/v1/todos', data)
  },

  // Update TODO (PATCH)
  updateTodo(id, data) {
    return api.patch(`/v1/todos/${id}`, data)
  },

  // Delete TODO
  deleteTodo(id) {
    return api.delete(`/v1/todos/${id}`)
  },

  // Batch complete TODOs
  batchCompleteTodos(todoIds) {
    return api.post('/v1/todos/batch', {
      todo_ids: todoIds
    })
  },

  // Get TODO statistics
  getTodoStats() {
    return api.get('/v1/todos/stats')
  }
}

export default todosApi
