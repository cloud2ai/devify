import { defineStore } from 'pinia'
import { detectTimezone, detectLanguage } from '@/utils/timezone'
import i18n from '@/i18n'

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
      this.language = language
      i18n.global.locale.value = language
      localStorage.setItem('userLanguage', language)
    },

    setTimezone(timezone) {
      this.timezone = timezone
      localStorage.setItem('userTimezone', timezone)
    },

    loadFromLocalStorage() {
      const savedLanguage = localStorage.getItem('userLanguage')
      const savedTimezone = localStorage.getItem('userTimezone')

      if (savedLanguage) {
        this.language = savedLanguage
        i18n.global.locale.value = savedLanguage
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
