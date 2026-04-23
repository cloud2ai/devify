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

// Create Vue i18n instance
const i18n = createI18n({
  legacy: false,
  locale: getInitialLanguage(),
  fallbackLocale: 'en',
  messages: {
    en: { ...en, ...adminEn },
    'zh-CN': { ...zhCN, ...adminZhCN },
    es: es
  }
})

export default i18n
