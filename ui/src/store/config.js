import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { configApi } from '@/api/config'

export const useConfigStore = defineStore('config', () => {
  // State
  const smtpConfig = ref({
    host: '',
    port: 587,
    username: '',
    password: '',
    use_tls: true,
    from_email: '',
    from_name: ''
  })
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isSmtpConfigured = computed(() => {
    return (
      smtpConfig.value.host &&
      smtpConfig.value.username &&
      smtpConfig.value.password &&
      smtpConfig.value.from_email
    )
  })

  // Actions
  const loadSmtpConfig = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await configApi.getSmtpConfig()
      // Handle the actual response format from backend
      const responseData = response.data.data || response.data
      // Handle paginated response or direct data
      const data = responseData.list || responseData.results || responseData

      if (Array.isArray(data) && data.length > 0) {
        // Find SMTP config from settings list
        const smtpSetting = data.find((setting) => setting.category === 'smtp')
        if (smtpSetting && smtpSetting.value) {
          smtpConfig.value = JSON.parse(smtpSetting.value)
        }
      } else if (data && data.value) {
        smtpConfig.value = JSON.parse(data.value)
      } else {
        smtpConfig.value = data
      }
      return smtpConfig.value
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to load config'
      throw err
    } finally {
      loading.value = false
    }
  }

  const saveSmtpConfig = async (configData) => {
    loading.value = true
    error.value = null

    try {
      const response = await configApi.saveSmtpConfig(configData)
      // Handle the actual response format from backend
      const responseData = response.data.data || response.data
      if (responseData && responseData.value) {
        smtpConfig.value = JSON.parse(responseData.value)
      } else {
        smtpConfig.value = responseData
      }
      return smtpConfig.value
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to save config'
      throw err
    } finally {
      loading.value = false
    }
  }

  const testSmtpConfig = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await configApi.testSmtpConfig()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'SMTP test failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    smtpConfig,
    loading,
    error,
    // Getters
    isSmtpConfigured,
    // Actions
    loadSmtpConfig,
    saveSmtpConfig,
    testSmtpConfig
  }
})
