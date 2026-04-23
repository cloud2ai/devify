import { ref, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreferencesStore } from '@/store/preferences'
import { extractErrorMessage } from '@/utils/api'
import { chatApi } from '@/api/chat'

/**
 * Composable for managing threadline content editing (title, details, key process)
 * @param {Object} threadline - Reactive threadline ref
 * @param {Object} route - Vue router route object
 * @param {Function} getSummaryData - Function that returns summary data
 * @returns {Object} Content-related state and methods
 */
export function useThreadlineContent(threadline, route, getSummaryData) {
  const { t } = useI18n()
  const preferencesStore = usePreferencesStore()

  // Copy states
  const copiedStates = ref({
    summary: false,
    llm: false,
    details: false,
    keyProcess: false
  })

  // Title editing
  const editingTitle = ref(false)
  const editingTitleValue = ref('')
  const savingTitle = ref(false)
  const titleError = ref('')
  const titleInputRef = ref(null)

  // Details editing
  const savingDetails = ref(false)
  const detailsError = ref('')
  const editingDetails = ref(false)
  const detailsEditorRef = ref(null)

  // Key process editing
  const editingKeyProcess = ref(false)
  const savingKeyProcess = ref(false)
  const keyProcessError = ref('')
  const keyProcessEditorRef = ref(null)

  // Computed: Summary data
  const summaryData = computed(() => getSummaryData())

  // Computed: Details value
  const detailsValue = computed({
    get: () => summaryData.value.details || '',
    set: (val) => {
      if (!threadline.value) return
      if (!threadline.value.summary_data) {
        threadline.value.summary_data = {}
      }
      threadline.value.summary_data = {
        ...threadline.value.summary_data,
        details: val
      }
    }
  })

  // Computed: Key process value
  const keyProcessValue = computed({
    get: () => summaryData.value.key_process || [],
    set: (val) => {
      if (!threadline.value) return
      if (!threadline.value.summary_data) {
        threadline.value.summary_data = {}
      }
      threadline.value.summary_data = {
        ...threadline.value.summary_data,
        key_process: val
      }
    }
  })

  // Title methods
  const startEditingTitle = () => {
    editingTitleValue.value =
      threadline.value?.summary_title || threadline.value?.subject || ''
    editingTitle.value = true
    nextTick(() => {
      if (titleInputRef.value) {
        titleInputRef.value.focus()
      }
    })
  }

  const cancelEditingTitle = () => {
    editingTitle.value = false
    editingTitleValue.value = ''
    titleError.value = ''
  }

  const saveTitle = async () => {
    if (!threadline.value) return
    savingTitle.value = true
    titleError.value = ''

    const id = route.params.id
    const originalTitle = threadline.value.summary_title

    try {
      const response = await chatApi.updateThreadline(id, {
        summary_title: editingTitleValue.value.trim()
      })
      const updatedData = response.data.data || response.data
      threadline.value = { ...threadline.value, ...updatedData }
      editingTitle.value = false
    } catch (err) {
      console.error('Failed to save title:', err)
      titleError.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('common.save')
      )
    } finally {
      savingTitle.value = false
    }
  }

  // Details methods
  const cancelEditingDetails = () => {
    detailsError.value = ''
    editingDetails.value = false
  }

  const saveDetails = async (value) => {
    if (!threadline.value) return
    savingDetails.value = true
    detailsError.value = ''

    const id = route.params.id
    const currentSummaryData = threadline.value.summary_data || {}
    const originalDetails = currentSummaryData.details

    try {
      const updatedSummaryData = {
        ...currentSummaryData,
        details: value
      }
      const response = await chatApi.updateThreadline(id, {
        summary_data: updatedSummaryData
      })
      const updatedData = response.data.data || response.data
      threadline.value = { ...threadline.value, ...updatedData }
      editingDetails.value = false
    } catch (err) {
      console.error('Failed to save details:', err)
      detailsError.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('common.save')
      )
      if (threadline.value.summary_data) {
        threadline.value.summary_data.details = originalDetails
      }
    } finally {
      savingDetails.value = false
    }
  }

  // Key process methods
  const cancelEditingKeyProcess = () => {
    keyProcessError.value = ''
    editingKeyProcess.value = false
  }

  const saveKeyProcess = async (value) => {
    if (!threadline.value) return
    savingKeyProcess.value = true
    keyProcessError.value = ''

    const id = route.params.id
    const currentSummaryData = threadline.value.summary_data || {}
    const originalKeyProcess = currentSummaryData.key_process

    try {
      const updatedSummaryData = {
        ...currentSummaryData,
        key_process: value
      }
      const response = await chatApi.updateThreadline(id, {
        summary_data: updatedSummaryData
      })
      const updatedData = response.data.data || response.data
      threadline.value = { ...threadline.value, ...updatedData }
      editingKeyProcess.value = false
    } catch (err) {
      console.error('Failed to save key process:', err)
      keyProcessError.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('common.save')
      )
      if (threadline.value.summary_data) {
        threadline.value.summary_data.key_process = originalKeyProcess
      }
    } finally {
      savingKeyProcess.value = false
    }
  }

  // Copy content function
  const copyContent = async (content, section) => {
    if (!content) return

    try {
      // Extract plain text from markdown content
      let textContent = content
        .replace(/```[\s\S]*?```/g, '')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/^#+\s+/gm, '')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/__([^_]+)__/g, '$1')
        .replace(/_([^_]+)_/g, '$1')
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
        .replace(/!\[([^\]]*)\]\([^\)]+\)/g, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim()

      await navigator.clipboard.writeText(textContent)
      copiedStates.value[section] = true
      setTimeout(() => {
        copiedStates.value[section] = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy content:', error)
    }
  }

  const openDetailsEditor = () => {
    if (editingDetails.value) return
    editingDetails.value = true
    nextTick(() => {
      if (
        detailsEditorRef.value &&
        typeof detailsEditorRef.value.startEditing === 'function'
      ) {
        detailsEditorRef.value.startEditing()
      }
    })
  }

  const openKeyProcessEditor = () => {
    if (editingKeyProcess.value) return
    editingKeyProcess.value = true
    nextTick(() => {
      if (
        keyProcessEditorRef.value &&
        typeof keyProcessEditorRef.value.startEditing === 'function'
      ) {
        keyProcessEditorRef.value.startEditing()
      }
    })
  }

  const copyKeyProcess = async () => {
    const keyProcess = summaryData.value?.key_process || []
    if (keyProcess.length === 0) return

    try {
      const text = keyProcess
        .map((item, index) => `${index + 1}. ${item}`)
        .join('\n')
      await navigator.clipboard.writeText(text)
      copiedStates.value.keyProcess = true
      setTimeout(() => {
        copiedStates.value.keyProcess = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy key process:', error)
    }
  }

  return {
    // State
    copiedStates,
    editingTitle,
    editingTitleValue,
    savingTitle,
    titleError,
    titleInputRef,
    savingDetails,
    detailsError,
    editingDetails,
    detailsEditorRef,
    editingKeyProcess,
    savingKeyProcess,
    keyProcessError,
    keyProcessEditorRef,
    // Computed
    detailsValue,
    keyProcessValue,
    // Methods
    startEditingTitle,
    cancelEditingTitle,
    saveTitle,
    cancelEditingDetails,
    saveDetails,
    cancelEditingKeyProcess,
    saveKeyProcess,
    copyContent,
    openDetailsEditor,
    openKeyProcessEditor,
    copyKeyProcess
  }
}
