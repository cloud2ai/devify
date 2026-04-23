import apiClient from './index'

export const settingsApi = {
  async getSettings() {
    const response = await apiClient.get('/v1/settings')
    return response.data
  },

  async getSetting(id) {
    const response = await apiClient.get(`/v1/settings/${id}`)
    return response.data
  },

  async createSetting(data) {
    const response = await apiClient.post('/v1/settings', data)
    return response.data
  },

  async updateSetting(id, data) {
    const response = await apiClient.patch(`/v1/settings/${id}`, data)
    return response.data
  },

  async deleteSetting(id) {
    const response = await apiClient.delete(`/v1/settings/${id}`)
    return response.data
  },

  async updatePreferences(preferences) {
    const settings = await this.getSettings()
    const preferencesData = settings.data?.list || settings.data || []

    const promptConfigSetting = preferencesData.find(
      (s) => s.key === 'prompt_config'
    )

    const promises = []

    if (promptConfigSetting) {
      const currentValue = promptConfigSetting.value || {}
      const updatedValue = { ...currentValue }

      if (preferences.language) {
        updatedValue.language = preferences.language
      }

      if (preferences.scene) {
        updatedValue.scene = preferences.scene
      }

      promises.push(
        this.updateSetting(promptConfigSetting.id, {
          value: updatedValue
        })
      )
    } else {
      const promptConfigValue = {}

      if (preferences.language) {
        promptConfigValue.language = preferences.language
      }

      if (preferences.scene) {
        promptConfigValue.scene = preferences.scene
      }

      if (Object.keys(promptConfigValue).length > 0) {
        promises.push(
          this.createSetting({
            key: 'prompt_config',
            value: promptConfigValue,
            description: 'User prompt configuration (language and scene)'
          })
        )
      }
    }

    await Promise.all(promises)
  },

  async getPreferences() {
    const settings = await this.getSettings()
    const settingsData = settings.data?.list || settings.data || []

    const promptConfigSetting = settingsData.find(
      (s) => s.key === 'prompt_config'
    )

    return {
      language: promptConfigSetting?.value?.language || null,
      scene: promptConfigSetting?.value?.scene || null
    }
  },

  async getEmailAliases() {
    const response = await apiClient.get('/v1/settings/email-aliases')
    return response.data
  },

  async createEmailAlias(alias) {
    const response = await apiClient.post('/v1/settings/email-aliases', {
      alias
    })
    return response.data
  },

  async deleteEmailAlias(id) {
    const response = await apiClient.delete(`/v1/settings/email-aliases/${id}`)
    return response.data
  },

  async validateAlias(alias) {
    const response = await apiClient.post(
      '/v1/settings/email-aliases/validate',
      { alias }
    )
    return response.data
  }
}
