import { defineStore } from 'pinia'
import { detectTimezone, detectLanguage } from '@/utils/timezone'
import i18n from '@/i18n'

function normalizeUiLanguage(language) {
  if (!language || typeof language !== 'string') {
    return 'en'
  }

  const value = language.trim().toLowerCase()
  if (value.startsWith('zh')) {
    return 'zh-CN'
  }
  if (value.startsWith('es')) {
    return 'es'
  }
  return 'en'
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    language: detectLanguage(),
    timezone: detectTimezone(),
    detectedLanguage: detectLanguage(),
    detectedTimezone: detectTimezone(),
    isLoaded: false
  }),

  getters: {
    currentLanguage: (state) => state.language,
    currentTimezone: (state) => state.timezone,
    isAutoDetected: (state) => {
      return (
        state.language === state.detectedLanguage &&
        state.timezone === state.detectedTimezone
      )
    }
  },

  actions: {
    setLanguage(language) {
      const normalizedLanguage = normalizeUiLanguage(language)
      this.language = normalizedLanguage
      i18n.global.locale.value = normalizedLanguage
      localStorage.setItem('userLanguage', normalizedLanguage)
    },

    setTimezone(timezone) {
      this.timezone = timezone
      localStorage.setItem('userTimezone', timezone)
    },

    loadFromLocalStorage() {
      const savedLanguage = localStorage.getItem('userLanguage')
      const savedTimezone = localStorage.getItem('userTimezone')

      if (savedLanguage) {
        this.setLanguage(savedLanguage)
      }

      if (savedTimezone) {
        this.timezone = savedTimezone
      }

      this.isLoaded = true
    },

    loadFromBackend(preferences) {
      if (preferences.language) {
        this.setLanguage(preferences.language)
      }

      if (preferences.scene) {
        // Store scene preference if needed
        localStorage.setItem('userScene', preferences.scene)
      }

      this.isLoaded = true
    },

    reset() {
      this.language = this.detectedLanguage
      this.timezone = this.detectedTimezone
      i18n.global.locale.value = this.detectedLanguage
      localStorage.removeItem('userLanguage')
      localStorage.removeItem('userTimezone')
    }
  }
})
