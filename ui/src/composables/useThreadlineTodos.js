import { ref, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import { todosApi } from '@/api/todos'

/**
 * Composable for managing threadline todos
 * @param {Object} threadline - Reactive threadline ref
 * @returns {Object} Todo-related state and methods
 */
export function useThreadlineTodos(threadline) {
  const { t } = useI18n()
  const toast = useToast()

  // Todo state
  const showTodoEditor = ref(false)
  const editingTodo = ref(null)
  const savingTodo = ref(false)
  const todoLoading = ref({})
  const todoErrorMessage = ref('')
  const todoSuccessMessage = ref('')
  const tempNewTodo = ref(null)
  const savingNewTodo = ref(false)
  const editingTodoIds = ref(new Set())

  // Computed: Sorted todos
  const threadlineTodos = computed(() => {
    if (!threadline.value || !threadline.value.todos) {
      return []
    }

    const todos = [...threadline.value.todos]

    // Sort by deadline from earliest to latest
    return todos.sort((a, b) => {
      if (!a.deadline && !b.deadline) return 0
      if (!a.deadline) return 1 // No deadline goes to end
      if (!b.deadline) return -1
      return new Date(a.deadline) - new Date(b.deadline)
    })
  })

  const handleAddTodo = () => {
    if (!threadline.value || !threadline.value.id) {
      todoErrorMessage.value =
        t('todos.error.noEmailMessage') ||
        'Cannot create TODO: Email message not loaded'
      return
    }

    // Create temporary todo with default values
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hours = String(now.getHours()).padStart(2, '0')
    const minutes = String(now.getMinutes()).padStart(2, '0')

    tempNewTodo.value = {
      id: `temp-${Date.now()}`,
      content: '',
      priority: null,
      owner: '',
      deadline: `${year}-${month}-${day}T${hours}:${minutes}`,
      location: '',
      is_completed: false,
      isNew: true
    }
  }

  const saveNewTodo = async (todoId, todoData) => {
    // Validate - content is required
    if (!todoData.content || !todoData.content.trim()) {
      throw new Error(
        t('todos.content') + ' ' + (t('common.required') || '必填')
      )
    }

    savingNewTodo.value = true
    todoErrorMessage.value = ''
    todoSuccessMessage.value = ''
    const tempId = tempNewTodo.value?.id

    try {
      const response = await todosApi.createTodo({
        ...todoData,
        email_message_id: threadline.value?.id
      })
      const newTodo = response.data.data || response.data

      // Add new todo to actual todos list
      if (threadline.value) {
        if (!threadline.value.todos) {
          threadline.value.todos = []
        }
        threadline.value.todos.push(newTodo)
      }

      await nextTick()

      // Clear editing state for the temp todo
      if (tempId) {
        editingTodoIds.value.delete(tempId)
      }

      // Clear tempNewTodo to re-enable the add button
      tempNewTodo.value = null

      todoSuccessMessage.value =
        t('todos.createSuccess') || 'TODO created successfully'

      setTimeout(() => {
        todoSuccessMessage.value = ''
      }, 3000)
    } catch (err) {
      console.error('Failed to create todo:', err)
      // Clear editing state even on error
      if (tempId) {
        editingTodoIds.value.delete(tempId)
      }
      todoErrorMessage.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('todos.save')
      )
      throw err
    } finally {
      savingNewTodo.value = false
    }
  }

  const cancelNewTodo = () => {
    if (tempNewTodo.value) {
      editingTodoIds.value.delete(tempNewTodo.value.id)
    }
    tempNewTodo.value = null
  }

  const handleTodoEditingChange = (todoId, isEditing) => {
    if (!todoId) {
      console.warn('handleTodoEditingChange called without todoId')
      return
    }

    if (isEditing) {
      editingTodoIds.value.add(todoId)
    } else {
      editingTodoIds.value.delete(todoId)
    }
  }

  const handleEditTodo = (todo) => {
    editingTodo.value = todo
    showTodoEditor.value = true
  }

  const handleSaveTodoInline = async (todoId, todoData) => {
    todoLoading.value[todoId] = true
    todoErrorMessage.value = ''
    todoSuccessMessage.value = ''
    try {
      const response = await todosApi.updateTodo(todoId, todoData)
      const updatedTodo = response.data.data || response.data

      // Update local state instead of reloading entire threadline
      if (threadline.value && threadline.value.todos) {
        const index = threadline.value.todos.findIndex((t) => t.id === todoId)
        if (index !== -1) {
          threadline.value.todos[index] = updatedTodo
        }
      }

      todoSuccessMessage.value =
        t('todos.updateSuccess') || 'TODO updated successfully'

      setTimeout(() => {
        todoSuccessMessage.value = ''
      }, 3000)
    } catch (err) {
      console.error('Failed to save todo:', err)
      todoErrorMessage.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('todos.save')
      )
      throw err
    } finally {
      todoLoading.value[todoId] = false
    }
  }

  const handleSaveTodo = async (todoData) => {
    savingTodo.value = true
    todoErrorMessage.value = ''
    todoSuccessMessage.value = ''
    try {
      if (editingTodo.value) {
        const response = await todosApi.updateTodo(
          editingTodo.value.id,
          todoData
        )
        const updatedTodo = response.data.data || response.data

        // Update local state instead of reloading entire threadline
        if (threadline.value && threadline.value.todos) {
          const index = threadline.value.todos.findIndex(
            (t) => t.id === editingTodo.value.id
          )
          if (index !== -1) {
            threadline.value.todos[index] = updatedTodo
          }
        }

        todoSuccessMessage.value =
          t('todos.updateSuccess') || 'TODO updated successfully'
      } else {
        const response = await todosApi.createTodo(todoData)
        const newTodo = response.data.data || response.data

        // Add new todo to local state instead of reloading entire threadline
        if (threadline.value) {
          if (!threadline.value.todos) {
            threadline.value.todos = []
          }
          threadline.value.todos.push(newTodo)
        }

        todoSuccessMessage.value =
          t('todos.createSuccess') || 'TODO created successfully'
      }
      showTodoEditor.value = false
      editingTodo.value = null

      setTimeout(() => {
        todoSuccessMessage.value = ''
      }, 3000)
    } catch (err) {
      console.error('Failed to save todo:', err)
      todoErrorMessage.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('todos.save')
      )
    } finally {
      savingTodo.value = false
    }
  }

  const handleToggleTodo = async (todoId) => {
    todoLoading.value[todoId] = true
    todoErrorMessage.value = ''
    try {
      const todo = threadlineTodos.value.find((t) => t.id === todoId)
      if (!todo) return

      const response = await todosApi.updateTodo(todoId, {
        is_completed: !todo.is_completed
      })
      const updatedTodo = response.data.data || response.data

      // Update local state instead of reloading entire threadline
      if (threadline.value && threadline.value.todos) {
        const index = threadline.value.todos.findIndex((t) => t.id === todoId)
        if (index !== -1) {
          threadline.value.todos[index] = updatedTodo
        }
      }
    } catch (err) {
      console.error('Failed to toggle todo:', err)
      todoErrorMessage.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('todos.markCompleted')
      )
    } finally {
      todoLoading.value[todoId] = false
    }
  }

  const handleDeleteTodo = async (todoId) => {
    todoLoading.value[todoId] = true
    todoErrorMessage.value = ''
    try {
      await todosApi.deleteTodo(todoId)

      // Remove todo from local state instead of reloading entire threadline
      if (threadline.value && threadline.value.todos) {
        threadline.value.todos = threadline.value.todos.filter(
          (t) => t.id !== todoId
        )
      }

      todoSuccessMessage.value =
        t('todos.deleteSuccess') || 'TODO deleted successfully'
      setTimeout(() => {
        todoSuccessMessage.value = ''
      }, 3000)
    } catch (err) {
      console.error('Failed to delete todo:', err)
      todoErrorMessage.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('todos.delete')
      )
    } finally {
      todoLoading.value[todoId] = false
    }
  }

  return {
    // State
    showTodoEditor,
    editingTodo,
    savingTodo,
    todoLoading,
    todoErrorMessage,
    todoSuccessMessage,
    tempNewTodo,
    savingNewTodo,
    editingTodoIds,
    // Computed
    threadlineTodos,
    // Methods
    handleAddTodo,
    saveNewTodo,
    cancelNewTodo,
    handleTodoEditingChange,
    handleEditTodo,
    handleSaveTodoInline,
    handleSaveTodo,
    handleToggleTodo,
    handleDeleteTodo
  }
}
