import api from './index'

export const configApi = {
  // Get user settings
  getSettings() {
    return api.get('/v1/settings')
  },

  // Get specific setting by ID
  getSetting(id) {
    return api.get(`/v1/settings/${id}`)
  },

  // Create new setting
  createSetting(settingData) {
    return api.post('/v1/settings', settingData)
  },

  // Update setting
  updateSetting(id, settingData) {
    return api.patch(`/v1/settings/${id}`, settingData)
  },

  // Delete setting
  deleteSetting(id) {
    return api.delete(`/v1/settings/${id}`)
  },

  // Get SMTP configuration (assuming it's stored in settings)
  getSmtpConfig() {
    return api.get('/v1/settings?category=smtp')
  },

  // Save configuration by category
  saveConfigByCategory(category, name, configData) {
    return api.post('/v1/settings', {
      category,
      name,
      value: JSON.stringify(configData),
      is_active: true
    })
  },

  // Update configuration by ID
  updateConfigById(id, configData) {
    return api.patch(`/v1/settings/${id}`, configData)
  },

  // Get configuration by category
  getConfigByCategory(category) {
    return api.get(`/v1/settings?category=${category}`)
  },

  // Save SMTP configuration (legacy support)
  saveSmtpConfig(configData) {
    return this.saveConfigByCategory('email', 'email_config', configData)
  },

  // Update SMTP configuration (legacy support)
  updateSmtpConfig(id, configData) {
    return this.updateConfigById(id, configData)
  },

  // Test SMTP configuration
  testSmtpConfig() {
    return api.post('/v1/settings/test-smtp')
  }
}
