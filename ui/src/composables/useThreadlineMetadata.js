import { ref } from 'vue'
import { metadataApi } from '@/api/metadata'

/**
 * Composable for managing threadline metadata editing
 * @param {Object} threadline - Reactive threadline ref
 * @param {Object} route - Vue router route object
 * @returns {Object} Metadata-related state and methods
 */
export function useThreadlineMetadata(threadline, route) {
  // Metadata editor state
  const showEditor = ref(false)
  const editorKey = ref('')
  const editorValue = ref(null)
  const savingKeys = ref(new Set())
  const errorsByKey = ref({})

  const openEdit = (key) => {
    editorKey.value = key
    editorValue.value = threadline.value?.metadata
      ? threadline.value.metadata[key]
      : null
    showEditor.value = true
  }

  const openAdd = () => {
    const k = prompt('Enter new metadata key')
    if (!k) return
    editorKey.value = k
    editorValue.value = ''
    showEditor.value = true
  }

  const closeEditor = () => {
    showEditor.value = false
  }

  const saveEditor = async (newValue) => {
    if (!threadline.value) return
    const id = route.params.id
    const key = editorKey.value

    const prev = threadline.value.metadata
      ? { ...threadline.value.metadata }
      : {}
    const next = { ...prev, [key]: newValue }

    threadline.value = { ...threadline.value, metadata: next }
    showEditor.value = false
    try {
      savingKeys.value.add(key)
      delete errorsByKey.value[key]
      await metadataApi.patchThreadlineMetadata(id, { [key]: newValue })
    } catch (err) {
      console.error('Failed to save metadata:', err)
      threadline.value = { ...threadline.value, metadata: prev }
      errorsByKey.value[key] = err?.response?.data?.message || '保存失败'
    } finally {
      savingKeys.value.delete(key)
    }
  }

  const onChipsChange = (key, value) => {
    if (!threadline.value) return
    const prev = threadline.value.metadata
      ? { ...threadline.value.metadata }
      : {}
    const next = { ...prev, [key]: value }
    threadline.value = { ...threadline.value, metadata: next }
  }

  const onChipsSave = async (key, value) => {
    if (!threadline.value) return
    const id = route.params.id
    const prev = threadline.value.metadata
      ? { ...threadline.value.metadata }
      : {}
    try {
      savingKeys.value.add(key)
      delete errorsByKey.value[key]
      const response = await metadataApi.patchThreadlineMetadata(id, {
        [key]: value
      })
      // Update local state with the saved value from response
      if (response && response.data && response.data.metadata) {
        threadline.value.metadata = response.data.metadata
      } else {
        // Fallback: update with the value we sent
        if (threadline.value.metadata) {
          threadline.value.metadata[key] = value
        } else {
          threadline.value.metadata = { [key]: value }
        }
      }
    } catch (err) {
      console.error('Failed to save metadata:', err)
      threadline.value = { ...threadline.value, metadata: prev }
      errorsByKey.value[key] = err?.response?.data?.message || '保存失败'
    } finally {
      savingKeys.value.delete(key)
    }
  }

  const isSaving = (key) => savingKeys.value.has(key)
  const fieldError = (key) => errorsByKey.value[key]

  return {
    // State
    showEditor,
    editorKey,
    editorValue,
    savingKeys,
    errorsByKey,
    // Methods
    openEdit,
    openAdd,
    closeEditor,
    saveEditor,
    onChipsChange,
    onChipsSave,
    isSaving,
    fieldError
  }
}
