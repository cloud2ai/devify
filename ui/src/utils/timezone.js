import { format, formatDistanceToNow } from 'date-fns'
import { formatInTimeZone, toZonedTime } from 'date-fns-tz'
import { zhCN } from 'date-fns/locale/zh-CN'
import { enUS } from 'date-fns/locale/en-US'
import { es } from 'date-fns/locale/es'

const localeMap = {
  'zh-CN': zhCN,
  en: enUS,
  es: es
}

export function detectTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch (error) {
    console.error('Failed to detect timezone:', error)
    return 'UTC'
  }
}

export function detectLanguage() {
  const browserLang = navigator.language || navigator.userLanguage

  if (browserLang.startsWith('zh')) {
    return 'zh-CN'
  }

  if (browserLang.startsWith('es')) {
    return 'es'
  }

  return 'en'
}

export function formatDate(
  date,
  timezone,
  pattern = 'yyyy-MM-dd HH:mm:ss',
  language = 'en'
) {
  if (!date) return ''

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date

    // Normalize language code to match localeMap keys
    let normalizedLanguage = language
    if (language && language.startsWith('zh')) {
      normalizedLanguage = 'zh-CN'
    } else if (language && language.startsWith('en')) {
      normalizedLanguage = 'en'
    } else if (language && language.startsWith('es')) {
      normalizedLanguage = 'es'
    }

    const locale = localeMap[normalizedLanguage] || enUS

    // date-fns formatInTimeZone supports Chinese characters in pattern string
    // The locale parameter affects relative time and month/day names, not the pattern itself
    const result = formatInTimeZone(dateObj, timezone || 'UTC', pattern, {
      locale
    })

    return result
  } catch (error) {
    console.error('Failed to format date:', error, {
      date,
      timezone,
      pattern,
      language
    })
    return ''
  }
}

export function formatRelativeTime(date, language = 'en') {
  if (!date) return ''

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    const locale = localeMap[language] || enUS

    return formatDistanceToNow(dateObj, { addSuffix: true, locale })
  } catch (error) {
    console.error('Failed to format relative time:', error)
    return ''
  }
}

export function convertToUserTimezone(date, timezone) {
  if (!date) return null

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    return toZonedTime(dateObj, timezone || 'UTC')
  } catch (error) {
    console.error('Failed to convert timezone:', error)
    return date
  }
}

// Get friendly language display name
export function getFriendlyLanguageName(languageCode) {
  const languageNames = {
    en: 'English',
    'zh-CN': '简体中文',
    zh: '简体中文',
    es: 'Español'
  }
  return languageNames[languageCode] || languageCode
}

// Get friendly timezone display with UTC offset
export function getFriendlyTimezoneName(timezone) {
  try {
    const now = new Date()
    const utcOffset = formatInTimeZone(now, timezone, 'XXX')
    const offsetHours = parseInt(utcOffset.substring(1, 3))
    const offsetMinutes = parseInt(utcOffset.substring(4, 6))
    const offsetSign = utcOffset.substring(0, 1)

    let gmtOffset = ''
    if (offsetHours === 0 && offsetMinutes === 0) {
      gmtOffset = 'GMT'
    } else {
      gmtOffset = `GMT${offsetSign}${offsetHours}`
      if (offsetMinutes > 0) {
        gmtOffset += `:${offsetMinutes.toString().padStart(2, '0')}`
      }
    }

    return `${timezone} (${gmtOffset})`
  } catch (error) {
    console.error('Failed to get friendly timezone name:', error)
    return timezone
  }
}

export function formatRelativeDate(dateString, t) {
  const date = new Date(dateString)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000)

  if (diff < 60) {
    return t('time.justNow')
  }

  if (diff < 3600) {
    const minutes = Math.floor(diff / 60)
    return t('time.minutesAgo', { count: minutes })
  }

  if (diff < 86400) {
    const hours = Math.floor(diff / 3600)
    return t('time.hoursAgo', { count: hours })
  }

  if (diff < 604800) {
    const days = Math.floor(diff / 86400)
    return t('time.daysAgo', { count: days })
  }

  return date.toLocaleDateString()
}
