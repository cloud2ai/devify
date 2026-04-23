import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { chatApi } from '@/api/chat'

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
  let retryPollInterval = null
  let retryPollStartTime = null

  const stopRetryPolling = () => {
    if (retryPollInterval) {
      clearInterval(retryPollInterval)
      retryPollInterval = null
    }
    retryPollStartTime = null
  }

  const pollThreadlineStatus = async () => {
    try {
      // Check if we've been polling too long
      if (
        retryPollStartTime &&
        Date.now() - retryPollStartTime > MAX_POLL_DURATION
      ) {
        stopRetryPolling()
        retrying.value = false
        console.warn('Polling timeout: exceeded maximum duration')
        return
      }

      const response = await chatApi.getThreadline(route.params.id)
      const data = response.data.data || response.data
      threadline.value = data

      // Check if processing is complete
      const status = data.status

      // Keep retrying state true if status is processing
      if (status === 'processing') {
        retrying.value = true
        // Continue polling, don't stop
        return
      }

      if (status === 'success' || status === 'failed') {
        // Processing complete, stop polling
        stopRetryPolling()
        retrying.value = false
      }
    } catch (err) {
      console.error('Failed to poll threadline status:', err)
      // On error, stop polling
      stopRetryPolling()
      retrying.value = false
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
      stopRetryPolling()
      retrying.value = false
      retryPollStartTime = null
      toast.showError(err.response?.data?.message || t('retry.retryError'))
    }
  }

  return {
    // State
    retrying,
    showRetryDialog,
    // Methods
    stopRetryPolling,
    pollThreadlineStatus,
    startPolling,
    handleRetryClick,
    handleRetry
  }
}
