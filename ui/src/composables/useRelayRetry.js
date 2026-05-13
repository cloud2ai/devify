import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { relayApi } from '@/api/relay'
import { extractErrorMessage } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { useRelayFormatters } from '@/composables/useRelayFormatters'

export function useRelayRetry({
  retrySelection,
  deliveryPagination,
  loadDeliveries,
  findEventByDeliveryId,
  markEventProcessing,
  activeTab
}) {
  const { t } = useI18n()
  const { showError, showSuccess, showWarning } = useToast()
  const { eventDeliveries } = useRelayFormatters()

  const retryingDeliveryId = ref('')
  const retryConfirm = reactive({
    show: false,
    title: '',
    message: '',
    note: '',
    confirmText: '',
    action: null
  })
  let retryPollToken = 0

  function eventRetryKey(event) {
    return String(event?.id || '')
  }

  function eventRetryLockKey(event) {
    return `event:${eventRetryKey(event)}`
  }

  function eventRetryMode(event) {
    const dels = eventDeliveries(event)
    if (dels.length === 0) return 'missing'
    if (dels.length === 1) return 'single'
    return 'all'
  }

  function eventRetryTarget(event) {
    const dels = eventDeliveries(event)
    if (dels.length === 0) return null
    const selection = retrySelection[eventRetryKey(event)]
    if (selection && selection !== 'all') {
      return dels.find((d) => String(d.id) === String(selection)) || null
    }
    return dels.find((d) => d.status === 'failed') || dels[0] || null
  }

  function isEventRetryBusy(event) {
    if (retryingDeliveryId.value === eventRetryLockKey(event)) {
      return true
    }

    if (String(event?.status || '').toLowerCase() === 'processing') {
      return true
    }

    return eventDeliveries(event).some(
      (delivery) =>
        String(delivery?.status || '').toLowerCase() === 'processing'
    )
  }

  function sleep(ms) {
    return new Promise((resolve) => {
      setTimeout(resolve, ms)
    })
  }

  function isDeliveryTerminal(status) {
    return ['SUCCESS', 'FAILED', 'SKIPPED'].includes(
      String(status || '').toUpperCase()
    )
  }

  function isEventTerminal(status) {
    return ['COMPLETED', 'FAILED'].includes(String(status || '').toUpperCase())
  }

  function openRetryConfirm({ title, message, note, confirmText, action }) {
    retryConfirm.title = title
    retryConfirm.message = message
    retryConfirm.note = note
    retryConfirm.confirmText = confirmText
    retryConfirm.action = action
    retryConfirm.show = true
  }

  function closeRetryConfirm() {
    retryConfirm.show = false
    retryConfirm.title = ''
    retryConfirm.message = ''
    retryConfirm.note = ''
    retryConfirm.confirmText = ''
    retryConfirm.action = null
  }

  async function confirmRetry() {
    if (typeof retryConfirm.action !== 'function') return
    const action = retryConfirm.action
    activeTab.value = 'deliveries'
    retryConfirm.show = false
    retryConfirm.title = ''
    retryConfirm.message = ''
    retryConfirm.note = ''
    retryConfirm.confirmText = ''
    retryConfirm.action = null
    await action()
  }

  async function waitForRelayCompletion(
    target,
    { timeoutMs = 30000, intervalMs = 2000, minDisplayMs = 1000 } = {}
  ) {
    const pollToken = ++retryPollToken
    const startedAt = Date.now()
    let currentInterval = intervalMs
    while (Date.now() - startedAt < timeoutMs) {
      if (pollToken !== retryPollToken) return null
      if (target.type === 'delivery') {
        const delivery = await relayApi.getDelivery(target.id)
        if (delivery?.status && isDeliveryTerminal(delivery.status)) {
          // Ensure minimum display time for processing state
          const elapsedMs = Date.now() - startedAt
          if (elapsedMs < minDisplayMs) {
            await sleep(minDisplayMs - elapsedMs)
          }
          return delivery
        }
      } else if (target.type === 'event') {
        const event = await relayApi.getEvent(target.id)
        const eventDels = Array.isArray(event?.deliveries)
          ? event.deliveries
          : []
        if (event?.status && isEventTerminal(event.status)) {
          // Ensure minimum display time for processing state
          const elapsedMs = Date.now() - startedAt
          if (elapsedMs < minDisplayMs) {
            await sleep(minDisplayMs - elapsedMs)
          }
          return event
        }
        if (
          eventDels.length &&
          eventDels.every((item) => isDeliveryTerminal(item.status))
        ) {
          // Ensure minimum display time for processing state
          const elapsedMs = Date.now() - startedAt
          if (elapsedMs < minDisplayMs) {
            await sleep(minDisplayMs - elapsedMs)
          }
          return event
        }
      }
      await sleep(currentInterval)
      currentInterval = Math.min(currentInterval * 2, 8000)
    }
    return null
  }

  async function retryDelivery(delivery, { refresh = true, lockId = '' } = {}) {
    if (!delivery?.id) {
      showError(t('common.error'))
      return
    }
    retryingDeliveryId.value = lockId || `delivery:${delivery.id}`
    try {
      const result = await relayApi.retryDelivery(delivery.id)
      markEventProcessing(findEventByDeliveryId(delivery.id), delivery.id)
      if (result?.task_rebuilt) {
        showWarning(t('relay.retryDeliveryQueuedWithTaskRebuild'))
      } else {
        showSuccess(t('relay.retryDeliveryQueued'))
      }
      const settled = await waitForRelayCompletion(
        { type: 'delivery', id: delivery.id },
        { timeoutMs: 30000, intervalMs: 2000 }
      )
      if (!settled) showWarning(t('relay.retryRelayTimeout'))
    } catch (error) {
      showError(extractErrorMessage(error, t('common.error')))
    } finally {
      if (refresh)
        await loadDeliveries({
          page: deliveryPagination.value.page,
          append: false
        })
      retryingDeliveryId.value = ''
    }
  }

  async function retryEvent(event, { refresh = true, lockId = '' } = {}) {
    if (!event?.id) return
    retryingDeliveryId.value = lockId || eventRetryLockKey(event)
    try {
      const result = await relayApi.retryEvent(event.id)
      markEventProcessing(event)
      if (result?.task_rebuilt) {
        showWarning(t('relay.retryDeliveryQueuedWithTaskRebuild'))
      } else {
        showSuccess(t('relay.retryDeliveryQueued'))
      }
      const settled = await waitForRelayCompletion(
        { type: 'event', id: event.id },
        { timeoutMs: 30000, intervalMs: 2000 }
      )
      if (!settled) showWarning(t('relay.retryRelayTimeout'))

      if (refresh) {
        await loadDeliveries({
          page: deliveryPagination.value.page,
          append: false
        })
      }
    } catch (error) {
      showError(extractErrorMessage(error, t('common.error')))
    } finally {
      retryingDeliveryId.value = ''
    }
  }

  async function retryAllDeliveries(event) {
    openRetryConfirm({
      title: t('relay.retryConfirmTitle'),
      message: t('relay.retryConfirmMessage'),
      note: t('relay.retryConfirmTaskRebuildNote'),
      confirmText: t('relay.retryConfirmAction'),
      action: () => retryEvent(event, { lockId: eventRetryLockKey(event) })
    })
  }

  async function retrySelectedDelivery(event) {
    const delivery = eventRetryTarget(event)
    if (!delivery) return
    openRetryConfirm({
      title: t('relay.retryConfirmTitle'),
      message: t('relay.retryConfirmMessage'),
      note: t('relay.retryConfirmTaskRebuildNote'),
      confirmText: t('relay.retryConfirmAction'),
      action: () =>
        retryDelivery(delivery, { lockId: eventRetryLockKey(event) })
    })
  }

  async function retryWithSelection(event) {
    const selection = retrySelection[eventRetryKey(event)] || 'all'
    if (selection === 'all') {
      await retryAllDeliveries(event)
      return
    }
    const delivery = eventDeliveries(event).find(
      (item) => String(item.id) === String(selection)
    )
    if (delivery) {
      openRetryConfirm({
        title: t('relay.retryConfirmTitle'),
        message: t('relay.retryConfirmMessage'),
        note: t('relay.retryConfirmTaskRebuildNote'),
        confirmText: t('relay.retryConfirmAction'),
        action: () =>
          retryDelivery(delivery, { lockId: eventRetryLockKey(event) })
      })
    }
  }

  return {
    retryingDeliveryId,
    retryConfirm,
    eventRetryKey,
    eventRetryLockKey,
    eventRetryMode,
    eventRetryTarget,
    isEventRetryBusy,
    isDeliveryTerminal,
    isEventTerminal,
    openRetryConfirm,
    closeRetryConfirm,
    confirmRetry,
    cancelAllPolls: () => {
      retryPollToken++
    },
    waitForRelayCompletion,
    retryDelivery,
    retryEvent,
    retryAllDeliveries,
    retrySelectedDelivery,
    retryWithSelection
  }
}
