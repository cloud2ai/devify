function getLocale(locale) {
  if (typeof locale === 'string' && locale.trim()) {
    return locale
  }
  return 'en-US'
}

function toNumber(value) {
  if (value == null || value === '') return null
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

export function formatNumLocale(value, locale) {
  const num = toNumber(value)
  if (num == null) return '-'
  return new Intl.NumberFormat(getLocale(locale), {
    maximumFractionDigits: 2
  }).format(num)
}

export function formatCostLocale(value, currency = 'USD', locale) {
  const num = toNumber(value)
  if (num == null) return '-'
  try {
    return new Intl.NumberFormat(getLocale(locale), {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 4
    }).format(num)
  } catch {
    return `${currency || 'USD'} ${num.toFixed(4)}`
  }
}

export function formatDateIsoLocale(value, locale) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString(getLocale(locale))
}

export function formatDuration(seconds) {
  const sec = toNumber(seconds)
  if (sec == null) return '-'
  if (sec < 1) return `${Math.round(sec * 1000)} ms`
  if (sec < 60) return `${sec.toFixed(2)} s`
  const minutes = Math.floor(sec / 60)
  const remaining = sec % 60
  if (minutes < 60) return `${minutes}m ${remaining.toFixed(0)}s`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
}
