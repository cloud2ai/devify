import { createI18n } from 'vue-i18n'

import en from '../locales/en.json'
import zhCN from '../locales/zh-CN.json'
import es from '../locales/es.json'
import adminEn from '@/admin/locales/en.json'
import adminZhCN from '@/admin/locales/zh-CN.json'

const supportedLanguages = ['en', 'zh-CN', 'es']

const normalizeLanguage = (lang) => {
  if (!lang || typeof lang !== 'string') {
    return 'en'
  }
  const value = lang.toLowerCase()
  if (value.includes('zh')) {
    return 'zh-CN'
  }
  if (value.includes('es')) {
    return 'es'
  }
  return 'en'
}

const detectBrowserLanguage = () => {
  if (typeof navigator === 'undefined') {
    return 'en'
  }
  const browserLang = navigator.language || navigator.userLanguage
  return normalizeLanguage(browserLang)
}

const getInitialLanguage = () => {
  const stored = localStorage.getItem('userLanguage')
  if (stored && supportedLanguages.includes(stored)) {
    return stored
  }
  return detectBrowserLanguage()
}

const isPlainObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value)

const mergeDeep = (base, override) => {
  if (!isPlainObject(base) || !isPlainObject(override)) {
    return override !== undefined ? override : base
  }

  const merged = { ...base }

  for (const [key, value] of Object.entries(override)) {
    if (isPlainObject(value) && isPlainObject(base[key])) {
      merged[key] = mergeDeep(base[key], value)
    } else {
      merged[key] = value
    }
  }

  return merged
}

const mergeCommonMessages = (base, override) => mergeDeep(base, override)

// Create Vue i18n instance
const i18n = createI18n({
  legacy: false,
  locale: getInitialLanguage(),
  fallbackLocale: 'en',
  messages: {
    en: mergeCommonMessages(en, adminEn),
    'zh-CN': mergeCommonMessages(zhCN, adminZhCN),
    es: es
  }
})

export default i18n
