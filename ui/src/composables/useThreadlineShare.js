import { ref, reactive, computed, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import { chatApi } from '@/api/chat'
import { formatDate as formatDateUtil } from '@/utils/timezone'

/**
 * Composable for managing threadline share functionality
 * @param {Object} threadline - Reactive threadline ref
 * @param {Object} route - Vue router route object
 * @returns {Object} Share-related state and methods
 */
export function useThreadlineShare(threadline, route) {
  const { t } = useI18n()
  const toast = useToast()

  // Share form state
  const shareForm = reactive({
    expiration: '7d',
    requirePassword: true,
    password: ''
  })

  // Share modal state
  const showShareModal = ref(false)
  const shareSaving = ref(false)
  const shareRevoking = ref(false)
  const shareError = ref('')
  const shareSuccessMessage = ref('')
  const sharePasswordDisplay = ref('')

  // Copy state
  const shareCopyState = reactive({
    link: false,
    password: false
  })

  // Inline share UI state
  const inlinePassword = ref('')
  const passwordSaving = ref(false)
  const editingPassword = ref(false)
  const tempPassword = ref('')
  const inlineExpiration = ref('30d')
  const expirationSaving = ref(false)
  const showPassword = ref(false)
  const editingExpiration = ref(false)
  const tempExpiration = ref('30d')
  const showShareLink = ref({
    main: false,
    quickShare: false,
    modal: false
  })

  // Note: shareStatus should be passed from parent or computed here
  // For now, we'll compute it from threadline
  const shareStatus = computed(() => threadline.value?.share_status || null)

  // Computed: Share expiration options
  const shareExpirationOptions = computed(() => [
    { value: '7d', label: t('share.option7d') },
    { value: '30d', label: t('share.option30d') },
    { value: 'forever', label: t('share.optionForever') }
  ])

  // Computed: Share expiration display
  const shareExpirationDisplay = computed(() => {
    if (!shareStatus.value || !shareStatus.value.is_active) {
      return ''
    }
    if (shareStatus.value.is_expired) {
      return t('share.statusExpired')
    }
    if (!shareStatus.value.expires_at) {
      return t('share.expirationForever')
    }
    return formatDateUtil(shareStatus.value.expires_at)
  })

  const resolveExpirationValue = () => {
    if (!shareStatus.value || !shareStatus.value.is_active) {
      return '30d'
    }

    if (shareStatus.value.is_expired) {
      return '30d'
    }

    if (!shareStatus.value.expires_at) {
      return 'forever'
    }

    const now = new Date()
    const expiry = new Date(shareStatus.value.expires_at)
    const diffDays = Math.round((expiry - now) / (1000 * 60 * 60 * 24))

    if (Math.abs(diffDays - 7) < 2) {
      return '7d'
    }

    if (Math.abs(diffDays - 30) < 2) {
      return '30d'
    }

    return '30d'
  }

  // Sync inline share state with share status
  const syncInlineShareState = () => {
    if (!shareStatus.value || !shareStatus.value.is_active) {
      inlinePassword.value = ''
      inlineExpiration.value = '30d'
      showPassword.value = false
      editingExpiration.value = false
      return
    }

    if (shareStatus.value.password) {
      inlinePassword.value = shareStatus.value.password
    } else {
      inlinePassword.value = ''
    }

    // Try to match expiration to options
    if (shareStatus.value.is_expired) {
      inlineExpiration.value = '30d'
    } else if (!shareStatus.value.expires_at) {
      inlineExpiration.value = 'forever'
    } else {
      // Basic heuristic: check days difference
      const now = new Date()
      const expiry = new Date(shareStatus.value.expires_at)
      const diffDays = Math.round((expiry - now) / (1000 * 60 * 60 * 24))
      if (Math.abs(diffDays - 7) < 2) inlineExpiration.value = '7d'
      else if (Math.abs(diffDays - 30) < 2) inlineExpiration.value = '30d'
      else inlineExpiration.value = '30d' // fallback
    }
  }

  // Watch share status changes
  watch(
    () => shareStatus.value,
    () => {
      syncInlineShareState()
    },
    { immediate: true }
  )

  // Quick share: create link directly (no modal)
  const handleQuickShare = async () => {
    if (!threadline.value) return

    // If share link already exists and is active, just copy it
    if (shareStatus.value?.is_active && !shareStatus.value.is_expired) {
      await copyShareLink()
      toast.showSuccess(t('share.linkCopied'))
      return
    }

    // If no share link exists, create new one
    shareSaving.value = true
    try {
      const payload = {
        expiration: '30d',
        require_password: true
      }

      const response = await chatApi.createShareLink(
        threadline.value.uuid || route.params.id,
        payload
      )
      const responseData = response.data.data || response.data
      sharePasswordDisplay.value = responseData.password || ''

      // Save password to share_status for copying
      const shareLinkData = responseData.share_link || responseData
      if (sharePasswordDisplay.value && shareLinkData) {
        shareLinkData.password = sharePasswordDisplay.value
      }
      threadline.value = {
        ...threadline.value,
        share_status: shareLinkData
      }

      // Wait for shareStatus to update
      await nextTick()

      // Auto copy
      await copyShareLink()
      toast.showSuccess(t('share.shareCreatedAndCopied'))
    } catch (err) {
      console.error('Share link creation failed:', err)
      toast.showError(
        extractErrorMessage(err, t('common.error') + ': ' + t('share.title'))
      )
    } finally {
      shareSaving.value = false
    }
  }

  // Open management modal
  const openShareModal = () => {
    if (!threadline.value) return
    shareForm.expiration = resolveExpirationValue()
    shareForm.requirePassword = shareStatus.value?.has_password ?? true
    // Generate 6-digit password
    shareForm.password = Math.floor(100000 + Math.random() * 900000).toString()
    sharePasswordDisplay.value = ''
    shareError.value = ''
    shareSuccessMessage.value = ''
    shareCopyState.link = false
    shareCopyState.password = false
    showShareModal.value = true
  }

  const closeShareModal = () => {
    if (shareSaving.value) {
      return
    }
    showShareModal.value = false
  }

  const handleShareSubmit = async () => {
    if (!threadline.value) return
    if (
      shareForm.requirePassword &&
      shareForm.password &&
      !/^\d{6}$/.test(shareForm.password.trim())
    ) {
      shareError.value = t('share.passwordFormatError')
      return
    }

    const wasShared = Boolean(shareStatus.value?.is_active)
    shareSaving.value = true
    shareError.value = ''
    shareSuccessMessage.value = ''

    try {
      const payload = {
        expiration: shareForm.expiration,
        require_password: shareForm.requirePassword
      }

      if (shareForm.requirePassword && shareForm.password.trim()) {
        payload.password = shareForm.password.trim()
      }

      const response = await chatApi.createShareLink(
        threadline.value.uuid || route.params.id,
        payload
      )
      const responseData = response.data.data || response.data
      sharePasswordDisplay.value = responseData.password || ''
      const shareLinkData = responseData.share_link || responseData
      if (sharePasswordDisplay.value && shareLinkData) {
        shareLinkData.password = sharePasswordDisplay.value
      }
      threadline.value = {
        ...threadline.value,
        share_status: shareLinkData
      }
      shareSuccessMessage.value = wasShared
        ? t('share.shareUpdated')
        : t('share.shareCreated')
    } catch (err) {
      console.error('Share link creation failed:', err)
      shareError.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('share.title')
      )
    } finally {
      shareSaving.value = false
    }
  }

  const handleStopSharing = () => {
    if (shareRevoking.value) {
      return
    }
    confirmStopSharing()
  }

  const confirmStopSharing = async () => {
    if (!shareStatus.value) {
      return
    }

    const shareToken = shareStatus.value.token || shareStatus.value.uuid
    if (!shareToken) {
      shareError.value = t('common.error') + ': ' + t('share.stopSharing')
      return
    }

    shareRevoking.value = true
    shareError.value = ''
    shareSuccessMessage.value = ''

    try {
      await chatApi.deleteShareLink(shareToken)
      threadline.value = {
        ...threadline.value,
        share_status: null
      }
      sharePasswordDisplay.value = ''
      shareSuccessMessage.value = t('share.shareRevoked')
      setTimeout(() => {
        closeShareModal()
      }, 1500)
    } catch (err) {
      console.error('Failed to revoke share link:', err)
      shareError.value = extractErrorMessage(
        err,
        t('common.error') + ': ' + t('share.stopSharing')
      )
    } finally {
      shareRevoking.value = false
    }
  }

  const generateLocalPassword = () => {
    // Generate 6-digit password
    const password = Math.floor(100000 + Math.random() * 900000).toString()
    shareForm.password = password
  }

  // Copy functions
  const copyLinkOnly = async () => {
    if (!shareStatus.value?.share_url) {
      return
    }
    try {
      await navigator.clipboard.writeText(shareStatus.value.share_url)
      shareCopyState.link = true
      setTimeout(() => {
        shareCopyState.link = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy link:', error)
    }
  }

  const copyShareLink = async () => {
    if (!shareStatus.value?.share_url) {
      return
    }
    try {
      let copyText = t('share.copyMessage', {
        url: shareStatus.value.share_url
      })
      const password = sharePasswordDisplay.value || shareStatus.value?.password
      if (shareStatus.value.has_password && password) {
        copyText += '\n' + t('share.passwordLabel') + ': ' + password
      }
      await navigator.clipboard.writeText(copyText)
      shareCopyState.link = true
      setTimeout(() => {
        shareCopyState.link = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy share link:', error)
    }
  }

  const copyFullInvite = async () => {
    if (!shareStatus.value?.share_url) return

    try {
      let copyText = t('share.copyMessage', {
        url: shareStatus.value.share_url
      })
      const password = sharePasswordDisplay.value || shareStatus.value?.password
      if (shareStatus.value.has_password && password) {
        copyText += '\n' + t('share.passwordLabel') + ': ' + password
      }
      await navigator.clipboard.writeText(copyText)
      shareCopyState.password = true
      setTimeout(() => {
        shareCopyState.password = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy full invite:', error)
    }
  }

  const copySharePassword = async () => {
    const password = sharePasswordDisplay.value || shareStatus.value?.password
    if (!password) {
      return
    }
    try {
      await navigator.clipboard.writeText(password)
      shareCopyState.password = true
      setTimeout(() => {
        shareCopyState.password = false
      }, 2000)
    } catch (error) {
      console.error('Failed to copy password:', error)
    }
  }

  // Password management
  const createRandomPassword = async () => {
    if (!threadline.value || !shareStatus.value) return
    passwordSaving.value = true
    try {
      // Generate 6-digit password
      const password = Math.floor(100000 + Math.random() * 900000).toString()
      await updateShareLink({ password, require_password: true })
      inlinePassword.value = password
      sharePasswordDisplay.value = password
      if (shareStatus.value) {
        shareStatus.value.password = password
        shareStatus.value.has_password = true
      }
    } catch (err) {
      console.error('Failed to create password:', err)
      toast.showError(extractErrorMessage(err, t('common.error')))
    } finally {
      passwordSaving.value = false
    }
  }

  const startEditingPassword = () => {
    if (!shareStatus.value || !shareStatus.value.has_password) return
    editingPassword.value = true
    tempPassword.value =
      inlinePassword.value || shareStatus.value.password || ''
  }

  const cancelEditingPassword = () => {
    editingPassword.value = false
    tempPassword.value = ''
  }

  const savePassword = async () => {
    if (!threadline.value || !shareStatus.value) return

    const trimmedPassword = tempPassword.value.trim()
    if (!trimmedPassword || !/^\d{6}$/.test(trimmedPassword)) {
      toast.showError(t('share.passwordFormatError'))
      return
    }

    passwordSaving.value = true
    try {
      await updateShareLink({
        password: trimmedPassword,
        require_password: true
      })
      inlinePassword.value = trimmedPassword
      sharePasswordDisplay.value = trimmedPassword
      if (shareStatus.value) {
        shareStatus.value.password = trimmedPassword
        shareStatus.value.has_password = true
      }
      editingPassword.value = false
      tempPassword.value = ''
      toast.showSuccess(t('share.passwordUpdated'))
    } catch (err) {
      console.error('Failed to update password:', err)
      toast.showError(extractErrorMessage(err, t('common.error')))
    } finally {
      passwordSaving.value = false
    }
  }

  const removePassword = async () => {
    if (!threadline.value || !shareStatus.value) return
    passwordSaving.value = true
    try {
      await updateShareLink({ password: null, require_password: false })
      inlinePassword.value = ''
      sharePasswordDisplay.value = ''
      editingPassword.value = false
      tempPassword.value = ''
      if (shareStatus.value) {
        shareStatus.value.password = null
        shareStatus.value.has_password = false
      }
      toast.showSuccess(t('share.passwordRemoved'))
    } catch (err) {
      console.error('Failed to remove password:', err)
      toast.showError(extractErrorMessage(err, t('common.error')))
    } finally {
      passwordSaving.value = false
    }
  }

  // Update share link (by recreating it with new settings)
  const updateShareLink = async (updates) => {
    if (!threadline.value) return

    const threadlineUuid = threadline.value.uuid || route.params.id
    if (!threadlineUuid) {
      throw new Error('Threadline UUID not found')
    }

    try {
      // Get current share status to preserve expiration if not updating it
      let currentExpiration = '7d'
      if (shareStatus.value?.expires_at) {
        if (shareStatus.value.is_expired) {
          currentExpiration = '7d'
        } else if (!shareStatus.value.expires_at) {
          currentExpiration = 'forever'
        } else {
          // Calculate days until expiration
          const expiresAt = new Date(shareStatus.value.expires_at)
          const now = new Date()
          const daysDiff = Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24))
          if (daysDiff <= 7) {
            currentExpiration = '7d'
          } else {
            currentExpiration = '30d'
          }
        }
      }

      // Prepare data for share link creation/update
      const shareData = {
        expiration:
          updates.expiration !== undefined
            ? updates.expiration
            : currentExpiration,
        require_password:
          updates.require_password !== undefined
            ? updates.require_password
            : (shareStatus.value?.has_password ?? true),
        password: updates.password !== undefined ? updates.password : ''
      }

      // If password is provided and not null/empty, ensure require_password is true
      if (
        updates.password !== undefined &&
        updates.password !== null &&
        updates.password !== ''
      ) {
        shareData.require_password = true
        shareData.password = updates.password
      }
      // If password is null or empty and require_password is explicitly false, set both
      else if (
        updates.password === null ||
        (updates.password === '' && updates.require_password === false)
      ) {
        shareData.require_password = false
        shareData.password = ''
      }
      // If require_password is true but no password provided, generate one
      else if (shareData.require_password && !shareData.password) {
        // Password will be auto-generated by backend
        shareData.password = ''
      }

      const response = await chatApi.createShareLink(threadlineUuid, shareData)
      const responseData = response.data.data || response.data
      const shareLinkData = responseData.share_link || responseData

      // Update threadline with new share status
      threadline.value = {
        ...threadline.value,
        share_status: {
          ...shareLinkData,
          password: responseData.password || shareLinkData.password || ''
        }
      }
    } catch (err) {
      console.error('Failed to update share link:', err)
      throw err
    }
  }

  // Expiration management
  const startEditingExpiration = () => {
    editingExpiration.value = true
    tempExpiration.value = inlineExpiration.value
  }

  const cancelEditingExpiration = () => {
    editingExpiration.value = false
  }

  const saveExpiration = async () => {
    if (!threadline.value || !shareStatus.value) return
    expirationSaving.value = true
    try {
      const expiration =
        tempExpiration.value === 'forever' ? null : tempExpiration.value
      await updateShareLink({ expiration })
      inlineExpiration.value = tempExpiration.value
      editingExpiration.value = false
    } catch (err) {
      console.error('Failed to save expiration:', err)
      toast.showError(extractErrorMessage(err, t('common.error')))
    } finally {
      expirationSaving.value = false
    }
  }

  return {
    // State
    shareForm,
    showShareModal,
    shareSaving,
    shareRevoking,
    shareError,
    shareSuccessMessage,
    sharePasswordDisplay,
    shareCopyState,
    inlinePassword,
    passwordSaving,
    editingPassword,
    tempPassword,
    inlineExpiration,
    expirationSaving,
    showPassword,
    editingExpiration,
    tempExpiration,
    showShareLink,
    // Computed
    shareStatus,
    shareExpirationOptions,
    shareExpirationDisplay,
    resolveExpirationValue,
    // Methods
    handleQuickShare,
    openShareModal,
    closeShareModal,
    handleShareSubmit,
    handleStopSharing,
    confirmStopSharing,
    generateLocalPassword,
    copyLinkOnly,
    copyShareLink,
    copyFullInvite,
    copySharePassword,
    createRandomPassword,
    removePassword,
    startEditingPassword,
    cancelEditingPassword,
    savePassword,
    updateShareLink,
    startEditingExpiration,
    cancelEditingExpiration,
    saveExpiration,
    syncInlineShareState
  }
}
