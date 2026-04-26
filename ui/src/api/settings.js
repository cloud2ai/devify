import apiClient from './index'

function extractSettingsList(response) {
  const payload = response?.data
  if (!payload) return []

  const data = payload.data ?? payload
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.list)) return data.list
  return []
}

export const settingsApi = {
  async getSettings(params = {}) {
    const response = await apiClient.get('/v1/settings', {
      params
    })
    return response.data
  },

  async getSettingsList() {
    const response = await this.getSettings({
      page_size: 100,
      ordering: 'key'
    })
    return extractSettingsList(response)
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

  async validateImapConfig(config) {
    const response = await apiClient.post('/v1/settings/test-imap', {
      value: config
    })
    return response.data
  },

  async testIssueConfig(config) {
    const response = await apiClient.post('/v1/settings/test-issue', {
      value: config
    })
    return response.data
  },

  async saveSettingByKey({ key, value, description, isActive = true }) {
    const settings = await this.getSettingsList()
    const existing = settings.find((setting) => setting.key === key)

    if (existing) {
      const response = await this.updateSetting(existing.id, {
        value,
        description:
          description !== undefined ? description : existing.description,
        is_active: isActive
      })
      return response.data || response
    }

    const response = await this.createSetting({
      key,
      value,
      description: description || '',
      is_active: isActive
    })
    return response.data || response
  },

  async getSettingByKey(key) {
    const settings = await this.getSettingsList()
    return settings.find((setting) => setting.key === key) || null
  },

  async updatePreferences(preferences) {
    const preferencesData = await this.getSettingsList()

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
    const settingsData = await this.getSettingsList()

    const promptConfigSetting = settingsData.find(
      (s) => s.key === 'prompt_config'
    )

    return {
      language: promptConfigSetting?.value?.language || null,
      scene: promptConfigSetting?.value?.scene || null
    }
  }
}
