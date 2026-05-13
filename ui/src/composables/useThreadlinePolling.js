import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { chatApi } from '@/api/chat'
import { isThreadlineProcessing } from '@/utils/threadlineStatus'

const MAX_POLL_DURATION = 5 * 60 * 1000 // 5 minutes max polling

/**
 * Composable for managing threadline status polling
 * @param {Object} threadline - Reactive threadline ref
 * @param {Object} route - Vue router route object
 * @returns {Object} Polling-related state and methods
 */
export function useThreadlinePolling(threadline, route) {
  const { t } = useI18n()
  const toast = useToast()

  const retrying = ref(false)
  const showRetryDialog = ref(false)
  const retryStartedAt = ref(null)
  let retryPollInterval = null
  let retryPollStartTime = null

  const stopRetryPolling = () => {
    if (retryPollInterval) {
      clearInterval(retryPollInterval)
      retryPollInterval = null
    }
    retryPollStartTime = null
  }

  const resetRetryState = () => {
    stopRetryPolling()
    retrying.value = false
    retryStartedAt.value = null
    showRetryDialog.value = false
  }

  const pollThreadlineStatus = async () => {
    try {
      // Check if we've been polling too long
      if (
        retryPollStartTime &&
        Date.now() - retryPollStartTime > MAX_POLL_DURATION
      ) {
        resetRetryState()
        console.warn('Polling timeout: exceeded maximum duration')
        return
      }

      const response = await chatApi.getThreadline(route.params.id)
      const data = response.data.data || response.data
      threadline.value = data
      const snapshotUpdatedAt = data?.updated_at
        ? Date.parse(data.updated_at)
        : null
      const isStaleRetrySnapshot =
        retrying.value &&
        Number.isFinite(retryStartedAt.value) &&
        Number.isFinite(snapshotUpdatedAt) &&
        snapshotUpdatedAt < retryStartedAt.value

      // Check if processing is complete
      // Keep retrying state true if status is processing
      if (isThreadlineProcessing(data)) {
        retrying.value = true
        // Continue polling, don't stop
        return
      }

      if (
        retrying.value &&
        isStaleRetrySnapshot &&
        (data.status === 'success' || data.status === 'failed')
      ) {
        return
      }

      if (data.status === 'success' || data.status === 'failed') {
        // Processing complete, stop polling
        resetRetryState()
      }
    } catch (err) {
      console.error('Failed to poll threadline status:', err)
      // On error, stop polling
      resetRetryState()
    }
  }

  const startPolling = () => {
    retrying.value = true
    stopRetryPolling() // Clear any existing polling
    retryPollStartTime = Date.now()
    retryPollInterval = setInterval(pollThreadlineStatus, 2000)
    // Poll immediately
    pollThreadlineStatus()
  }

  const handleRetryClick = (isProcessing, deleting) => {
    // Prevent opening dialog if already processing or retrying
    if (isProcessing || retrying.value || deleting) {
      return
    }
    showRetryDialog.value = true
  }

  const handleRetry = async (options) => {
    showRetryDialog.value = false
    retrying.value = true
    retryStartedAt.value = Date.now()

    try {
      await chatApi.retryThreadline(route.params.id, options)

      // Backend now immediately sets status to PROCESSING
      // Start polling for status updates right away
      stopRetryPolling() // Clear any existing polling
      retryPollStartTime = Date.now()
      retryPollInterval = setInterval(pollThreadlineStatus, 2000)

      // Poll immediately to get the updated status
      await pollThreadlineStatus()
    } catch (err) {
      console.error('Retry failed:', err)
      resetRetryState()
      toast.showError(err.response?.data?.message || t('retry.retryError'))
    }
  }

  return {
    // State
    retrying,
    showRetryDialog,
    retryStartedAt,
    // Methods
    stopRetryPolling,
    resetRetryState,
    pollThreadlineStatus,
    startPolling,
    handleRetryClick,
    handleRetry
  }
}
