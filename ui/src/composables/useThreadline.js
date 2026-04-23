import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePreferencesStore } from '@/store/preferences'
import { formatDate as formatDateUtil } from '@/utils/timezone'
import { extractErrorMessage } from '@/utils/api'
import { chatApi } from '@/api/chat'

/**
 * Composable for managing threadline core data
 * @param {Object} route - Vue router route object
 * @param {Function} startPolling - Optional function to start polling (from useThreadlinePolling)
 * @param {Object} threadlineRef - Optional shared threadline ref (if not provided, creates new one)
 * @returns {Object} Threadline-related state and methods
 */
export function useThreadline(
  route,
  startPolling = null,
  threadlineRef = null
) {
  const router = useRouter()
  const { t } = useI18n()
  const preferencesStore = usePreferencesStore()

  const threadline = threadlineRef || ref(null)
  const loading = ref(false)
  const error = ref('')
  const deleting = ref(false)
  const showDeleteConfirm = ref(false)
  const showActionMenu = ref(false)
  const actionMenuRef = ref(null)

  // Computed: Share status
  const shareStatus = computed(() => threadline.value?.share_status || null)

  // Computed: Check if email is currently processing
  const isProcessing = computed(() => {
    return threadline.value?.status === 'processing'
  })

  // Computed: Format detection
  const hasNewFormat = computed(() => {
    if (!threadline.value || !threadline.value.summary_data) {
      return false
    }
    let sd = threadline.value.summary_data
    // Handle string format (should be parsed by backend, but handle both)
    if (typeof sd === 'string') {
      try {
        sd = JSON.parse(sd)
      } catch (e) {
        return false
      }
    }
    return (
      (sd.details && sd.details.trim()) ||
      (Array.isArray(sd.key_process) && sd.key_process.length > 0)
    )
  })

  // Computed: Summary data
  const summaryData = computed(() => {
    if (!threadline.value || !threadline.value.summary_data) {
      return { details: '', key_process: [] }
    }
    let sd = threadline.value.summary_data
    // Handle string format (should be parsed by backend, but handle both)
    if (typeof sd === 'string') {
      try {
        sd = JSON.parse(sd)
      } catch (e) {
        return { details: '', key_process: [] }
      }
    }
    return {
      details: sd.details || '',
      key_process: sd.key_process || []
    }
  })

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

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return t('common.noData')

    // Use different date format based on language
    const dateFormat =
      preferencesStore.currentLanguage === 'zh-CN'
        ? 'yyyy年MM月dd日 HH:mm'
        : 'MMM dd, yyyy HH:mm'

    return formatDateUtil(
      dateString,
      preferencesStore.currentTimezone,
      dateFormat,
      preferencesStore.currentLanguage
    )
  }

  // Get status class
  const getStatusClass = (status) => {
    const statusMap = {
      success: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      processing: 'bg-yellow-100 text-yellow-800',
      fetched: 'bg-blue-100 text-blue-800'
    }
    return statusMap[status] || 'bg-gray-100 text-gray-800'
  }

  // Load threadline
  const loadThreadline = async () => {
    loading.value = true
    error.value = ''

    try {
      const response = await chatApi.getThreadline(route.params.id)
      // Handle the actual response format from backend
      const data = response.data.data || response.data
      threadline.value = data

      // If status is processing, start polling and show loading state
      if (data.status === 'processing') {
        if (startPolling) {
          startPolling()
        }
      }
    } catch (err) {
      console.error('Failed to load threadline:', err)

      // If resource not found (404), redirect to 404 page
      if (err.response?.status === 404) {
        router.push({ name: 'NotFound' })
        return
      }

      error.value = err.response?.data?.message || 'Failed to load threadline'
    } finally {
      loading.value = false
    }
  }

  // Delete threadline
  const deleteThreadline = async () => {
    showDeleteConfirm.value = true
  }

  const confirmDelete = async () => {
    showDeleteConfirm.value = false
    deleting.value = true

    try {
      await chatApi.deleteThreadline(route.params.id)
      router.push('/dashboard')
    } catch (err) {
      console.error('Delete failed:', err)
      // Error will be shown by toast in component
      throw err
    } finally {
      deleting.value = false
    }
  }

  // Go back
  const goBack = () => {
    if (window.history.length > 1) {
      router.back()
    } else {
      router.push('/dashboard')
    }
  }

  // Handle click outside
  const handleClickOutside = (event) => {
    if (
      actionMenuRef.value &&
      !actionMenuRef.value.contains(event.target) &&
      showActionMenu.value
    ) {
      showActionMenu.value = false
    }
  }

  return {
    // State
    threadline,
    loading,
    error,
    deleting,
    showDeleteConfirm,
    showActionMenu,
    actionMenuRef,
    // Computed
    shareStatus,
    isProcessing,
    hasNewFormat,
    summaryData,
    threadlineTodos,
    // Methods
    formatDate,
    getStatusClass,
    loadThreadline,
    deleteThreadline,
    confirmDelete,
    goBack,
    handleClickOutside
  }
}
