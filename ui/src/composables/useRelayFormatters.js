import { format as formatDate } from 'date-fns'
import { useI18n } from 'vue-i18n'

export function useRelayFormatters() {
  const { t } = useI18n()

  function targetLabel(targetType) {
    if (targetType === 'jira') return t('relay.targetJira')
    return t('relay.targetFeishu')
  }

  function targetIconBg(targetType) {
    if (targetType === 'jira') return 'bg-blue-600'
    return 'bg-primary-600'
  }

  function targetBadgeClass(targetType) {
    if (targetType === 'jira') return 'bg-sky-100 text-sky-700 ring-sky-200'
    return 'bg-primary-100 text-primary-700 ring-primary-200'
  }

  function eventStatusBadgeClass(status) {
    if (status === 'completed')
      return 'bg-green-100 text-green-700 ring-green-200'
    if (status === 'failed') return 'bg-red-100 text-red-700 ring-red-200'
    if (status === 'processing')
      return 'bg-yellow-100 text-yellow-700 ring-yellow-200'
    if (status === 'pending')
      return 'bg-blue-100 text-blue-700 ring-blue-200'
    return 'bg-gray-100 text-gray-600 ring-gray-200'
  }

  function targetIconPath(targetType) {
    if (targetType === 'jira') {
      return 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
    }
    return 'M13 10V3L4 14h7v7l9-11h-7z'
  }

  function statusClass(status) {
    if (status === 'success' || status === 'completed')
      return 'bg-green-100 text-green-700'
    if (status === 'failed') return 'bg-red-100 text-red-700'
    if (status === 'processing') return 'bg-blue-100 text-blue-700'
    if (status === 'pending') return 'bg-blue-100 text-blue-700'
    return 'bg-gray-100 text-gray-600'
  }

  function statusLabel(status) {
    if (status === 'success' || status === 'completed')
      return t('common.status.success')
    if (status === 'failed') return t('common.status.failed')
    if (status === 'processing') return t('common.status.processing')
    if (status === 'pending') return t('common.status.pending')
    return status
  }

  function statusIconPath(status) {
    if (status === 'success' || status === 'completed')
      return 'M9 12.75 11.25 15 15 9.75'
    if (status === 'failed') {
      return 'M12 9v4m0 4h.01M10.29 3.86l-7.05 12.21A2 2 0 0 0 4.97 19h14.06a2 2 0 0 0 1.73-2.93L13.71 3.86a2 2 0 0 0-3.42 0Z'
    }
    if (status === 'processing') return 'M12 6V12L16 14'
    if (status === 'pending') return 'M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z'
    return ''
  }

  function deliverySummaryTitle(delivery) {
    const snapshot =
      delivery?.event_artifact_snapshot || delivery?.artifact_snapshot || {}
    return (
      snapshot.summary_title ||
      snapshot.title ||
      snapshot.subject ||
      t('relay.deliveryFallbackTitle')
    )
  }

  function deliverySummaryContent(delivery) {
    const snapshot = delivery?.event_artifact_snapshot || {}
    return (
      snapshot.summary_content ||
      snapshot.llm_content ||
      snapshot.description ||
      ''
    )
  }

  function eventDeliveries(event) {
    return Array.isArray(event?.deliveries) ? event.deliveries : []
  }

  function toTimestamp(value) {
    if (!value) return 0
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? 0 : date.getTime()
  }

  function mergeEventRecords(items) {
    return [...items].sort(
      (a, b) =>
        toTimestamp(b.created_at || b.processed_at) -
        toTimestamp(a.created_at || a.processed_at)
    )
  }

  function eventMergeState(event) {
    return event?.email_message_merged_into_uuid ? 'original' : 'canonical'
  }

  function eventChatLink(event) {
    return `/chats/${event?.email_message_uuid || event?.email_message || event?.id || ''}`
  }

  function eventIssueTags(event) {
    return eventDeliveries(event)
      .filter((delivery) => delivery.external_id || delivery.external_url)
      .map((delivery, index) => ({
        key: `${delivery.subscription?.id || delivery.target_type || 'delivery'}:${delivery.external_id || delivery.id || index}`,
        label:
          delivery.external_id ||
          targetLabel(delivery.target_type) ||
          t('relay.openExternal'),
        url: delivery.external_url || '',
        title:
          delivery.external_url ||
          delivery.external_id ||
          t('relay.openExternal'),
        target_type: delivery.target_type
      }))
  }

  function eventPrimaryIssueTag(event) {
    const tags = eventIssueTags(event)
    return tags.length ? tags[0] : null
  }

  function formatDeliveryTime(value) {
    if (!value) return ''
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    try {
      return formatDate(date, 'yyyy-MM-dd HH:mm')
    } catch {
      return String(value)
    }
  }

  return {
    targetLabel,
    targetIconBg,
    targetBadgeClass,
    eventStatusBadgeClass,
    targetIconPath,
    statusClass,
    statusLabel,
    statusIconPath,
    deliverySummaryTitle,
    deliverySummaryContent,
    eventDeliveries,
    toTimestamp,
    mergeEventRecords,
    eventMergeState,
    eventChatLink,
    eventIssueTags,
    eventPrimaryIssueTag,
    formatDeliveryTime
  }
}
