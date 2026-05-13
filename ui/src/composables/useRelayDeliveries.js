import { useI18n } from 'vue-i18n'

/**
 * Shared composable for relay delivery display helpers.
 *
 * Used by Dashboard, ThreadlineDetail, and any other view that renders
 * relay delivery badges or links from an email/threadline item.
 */
export function useRelayDeliveries() {
  const { t } = useI18n()

  function isDisplayableDelivery(delivery) {
    return delivery?.status !== 'failed'
  }

  /**
   * Return the relay deliveries for an item, falling back to a synthetic
   * legacy entry when only the old issue_external_id field is present.
   */
  function getRelayDeliveries(item) {
    if (Array.isArray(item?.relay_deliveries) && item.relay_deliveries.length) {
      return item.relay_deliveries
        .filter(isDisplayableDelivery)
        .map((delivery) => ({
          ...delivery,
          external_url: delivery.external_url || item?.issue_url || ''
        }))
    }

    if (item?.issue_external_id) {
      return [
        {
          id: `legacy-${item.uuid || item.id || 'item'}`,
          target_type: 'legacy',
          external_id: item.issue_external_id,
          external_url: item.issue_url || '',
          subscription_name: null
        }
      ]
    }

    return []
  }

  /**
   * Human-readable label for a single delivery badge.
   */
  function relayDeliveryLabel(delivery) {
    if (!delivery) return t('relay.deliveryFallbackTitle')
    return (
      delivery.external_id ||
      delivery.subscription_name ||
      delivery.target_type ||
      t('relay.deliveryFallbackTitle')
    )
  }

  /**
   * Stable v-for key that is unique across all items and deliveries.
   *
   * Always prefixes with the parent item id so that two different items
   * whose deliveries share the same external_id never collide.
   */
  function relayDeliveryKey(item, delivery) {
    const itemId = item?.uuid || item?.id || 'item'
    const deliveryId =
      delivery?.id ??
      delivery?.external_id ??
      delivery?.target_type ??
      'delivery'
    return `${itemId}-${deliveryId}`
  }

  return { getRelayDeliveries, relayDeliveryLabel, relayDeliveryKey }
}
