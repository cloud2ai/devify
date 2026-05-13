import { nextTick, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { relayApi } from '@/api/relay'
import { extractErrorMessage } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import { useRelayFormatters } from '@/composables/useRelayFormatters'

export function useRelayDeliveryList({ loadSubscriptions, activeTab }) {
  const { t } = useI18n()
  const { showError } = useToast()
  const { mergeEventRecords, eventDeliveries } = useRelayFormatters()

  const loading = ref(false)
  const deliveries = ref([])
  const deliveryLoading = ref(false)
  const loadingMoreDeliveries = ref(false)
  const deliveryLoadMoreSentinel = ref(null)
  const retrySelection = reactive({})
  const deliveryPagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false
  })

  let deliveryLoadMoreObserver = null

  function findEventByDeliveryId(deliveryId) {
    return (
      deliveries.value.find((event) =>
        eventDeliveries(event).some(
          (item) => String(item.id) === String(deliveryId)
        )
      ) || null
    )
  }

  function markEventProcessing(event, deliveryId = null) {
    if (!event) return
    event.status = 'processing'
    if (!deliveryId) return
    const delivery = eventDeliveries(event).find(
      (item) => String(item.id) === String(deliveryId)
    )
    if (delivery) delivery.status = 'processing'
  }

  async function loadDeliveries({ page = 1, append = false } = {}) {
    if (append) {
      if (
        loadingMoreDeliveries.value ||
        deliveryLoading.value ||
        !deliveryPagination.value.hasNext
      )
        return
      loadingMoreDeliveries.value = true
    } else {
      if (deliveryLoading.value) return
      deliveryLoading.value = true
    }

    try {
      const data = await relayApi.getEvents({
        page,
        page_size: deliveryPagination.value.pageSize
      })
      const items = Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data)
          ? data
          : []

      // Preserve processing state from existing deliveries
      const processingStates = new Map()
      for (const event of deliveries.value) {
        if (event.status === 'processing') {
          processingStates.set(event.id, 'processing')
        }
        const dels = eventDeliveries(event)
        for (const delivery of dels) {
          if (delivery.status === 'processing') {
            processingStates.set(`delivery:${delivery.id}`, 'processing')
          }
        }
      }

      const combined = append ? [...deliveries.value, ...items] : items
      deliveries.value = mergeEventRecords(combined)

      // Restore processing state
      for (const event of deliveries.value) {
        if (
          processingStates.has(event.id) &&
          String(event.status || '').toLowerCase() === 'processing'
        ) {
          event.status = processingStates.get(event.id)
        }
        const dels = eventDeliveries(event)
        for (const delivery of dels) {
          if (
            processingStates.has(`delivery:${delivery.id}`) &&
            String(delivery.status || '').toLowerCase() === 'processing'
          ) {
            delivery.status = processingStates.get(`delivery:${delivery.id}`)
          }
        }
      }

      for (const item of items) {
        if (eventDeliveries(item).length > 1 && !retrySelection[item.id]) {
          retrySelection[item.id] = 'all'
        }
      }
      if (data?.pagination) {
        deliveryPagination.value = {
          page: data.pagination.page || page,
          pageSize:
            data.pagination.pageSize || deliveryPagination.value.pageSize,
          total: deliveries.value.length,
          totalPages: data.pagination.totalPages || 1,
          hasNext: Boolean(data.pagination.hasNext),
          hasPrevious: Boolean(data.pagination.hasPrevious)
        }
      } else {
        deliveryPagination.value = {
          ...deliveryPagination.value,
          page,
          total: deliveries.value.length,
          totalPages: 1,
          hasNext: false,
          hasPrevious: page > 1
        }
      }
    } finally {
      if (append) {
        loadingMoreDeliveries.value = false
      } else {
        deliveryLoading.value = false
      }
    }

    await nextTick()
    refreshDeliveryLoadMoreObserver()
  }

  async function reloadAll() {
    loading.value = true
    try {
      deliveryPagination.value.page = 1
      await Promise.all([
        loadSubscriptions(),
        loadDeliveries({ page: 1, append: false })
      ])
    } catch (error) {
      showError(extractErrorMessage(error, t('common.error')))
    } finally {
      loading.value = false
      deliveryLoading.value = false
      loadingMoreDeliveries.value = false
    }
    await nextTick()
    refreshDeliveryLoadMoreObserver()
  }

  function disconnectDeliveryLoadMoreObserver() {
    if (deliveryLoadMoreObserver) {
      deliveryLoadMoreObserver.disconnect()
      deliveryLoadMoreObserver = null
    }
  }

  function refreshDeliveryLoadMoreObserver() {
    disconnectDeliveryLoadMoreObserver()
    if (
      activeTab.value !== 'deliveries' ||
      !deliveryLoadMoreSentinel.value ||
      !deliveryPagination.value.hasNext ||
      loading.value ||
      deliveryLoading.value ||
      loadingMoreDeliveries.value
    ) {
      return
    }
    deliveryLoadMoreObserver = new IntersectionObserver(
      (entries) => {
        if (
          entries.some((entry) => entry.isIntersecting) &&
          activeTab.value === 'deliveries' &&
          deliveryPagination.value.hasNext &&
          !deliveryLoading.value &&
          !loadingMoreDeliveries.value
        ) {
          loadMoreDeliveries().catch((error) => {
            showError(extractErrorMessage(error, t('common.error')))
          })
        }
      },
      { root: null, rootMargin: '200px 0px', threshold: 0.1 }
    )
    deliveryLoadMoreObserver.observe(deliveryLoadMoreSentinel.value)
  }

  function loadMoreDeliveries() {
    if (
      !deliveryPagination.value.hasNext ||
      loading.value ||
      deliveryLoading.value ||
      loadingMoreDeliveries.value
    ) {
      return Promise.resolve()
    }
    return loadDeliveries({
      page: deliveryPagination.value.page + 1,
      append: true
    })
  }

  return {
    loading,
    deliveries,
    deliveryLoading,
    loadingMoreDeliveries,
    deliveryLoadMoreSentinel,
    retrySelection,
    deliveryPagination,
    findEventByDeliveryId,
    markEventProcessing,
    loadDeliveries,
    reloadAll,
    disconnectDeliveryLoadMoreObserver,
    refreshDeliveryLoadMoreObserver,
    loadMoreDeliveries
  }
}
