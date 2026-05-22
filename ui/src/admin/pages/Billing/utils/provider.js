export function normalizeProviderKey(providerKey, providerName) {
  return (providerKey || providerName || '').trim().toLowerCase()
}

export function formatProviderLabel(providerKey, providerName, t) {
  const normalized = normalizeProviderKey(providerKey, providerName)
  if (!normalized) {
    return '—'
  }
  if (normalized === 'platform') {
    return t('billing.users.sourcePlatform')
  }
  if (normalized === 'stripe') {
    return t('billing.users.sourceStripe')
  }
  return providerName || providerKey || '—'
}

export function isStripeProvider(providerKey, providerName) {
  return normalizeProviderKey(providerKey, providerName) === 'stripe'
}
