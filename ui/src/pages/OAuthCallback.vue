<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4"
  >
    <div class="max-w-md w-full space-y-8">
      <div v-if="processing" class="text-center py-12">
        <div
          class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"
        ></div>
        <p class="mt-4 text-gray-600">
          {{ t('auth.processing') || 'Processing...' }}
        </p>
      </div>

      <div v-else-if="needsSetup">
        <div class="mb-8">
          <div class="flex items-center justify-center">
            <h2 class="text-3xl font-extrabold text-gray-900">
              {{ t('register.complete.title') }}
            </h2>
            <div class="ml-3">
              <LanguageSwitcher />
            </div>
          </div>
          <p class="mt-2 text-center text-sm text-gray-600">
            {{
              t('register.oauthSetup.subtitle') ||
              'Please complete your profile setup'
            }}
          </p>
        </div>

        <form @submit.prevent="handleSubmit">
          <UserSetupForm
            ref="setupFormRef"
            :display-email="userEmail"
            :email-label="t('auth.email')"
            :loading="loading"
            :require-password="false"
            :initial-username="suggestedUsername"
            @submit="handleComplete"
          />
        </form>
      </div>

      <div
        v-else-if="error"
        class="rounded-md bg-red-50 border border-red-200 p-4"
      >
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="h-5 w-5 text-red-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">
              {{ t('auth.loginError') }}
            </h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ error }}</p>
            </div>
            <div class="mt-4">
              <router-link
                to="/register"
                class="text-sm font-medium text-red-600 hover:text-red-500"
              >
                {{ t('register.complete.backToRegister') }} →
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/user'
import { completeOAuthSetup } from '@/api/auth'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import UserSetupForm from '@/components/ui/UserSetupForm.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const processing = ref(true)
const needsSetup = ref(false)
const userEmail = ref('')
const suggestedUsername = ref('')
const error = ref('')
const loading = ref(false)
const setupFormRef = ref(null)

const handleSubmit = (e) => {
  e?.preventDefault()
}

const handleComplete = async (formValues) => {
  loading.value = true

  try {
    const response = await completeOAuthSetup({
      virtual_email_username: formValues.virtualEmailUsername,
      scene: formValues.scene,
      language: formValues.language,
      timezone: formValues.timezone
    })

    const responseData = response.data.data || response.data

    if (responseData.success || response.data.code === 0) {
      if (responseData.access) {
        localStorage.setItem('access_token', responseData.access)
      }
      if (responseData.refresh) {
        localStorage.setItem('refresh_token', responseData.refresh)
      }

      router.push('/chats')
    }
  } catch (err) {
    console.error('Setup completion error:', err)

    const errorData = err.response?.data?.data || err.response?.data

    if (errorData?.errors) {
      Object.keys(errorData.errors).forEach((key) => {
        setupFormRef.value?.setError(key, errorData.errors[key][0])
      })
    }

    if (errorData?.error) {
      setupFormRef.value?.setGeneralError(errorData.error)
    } else {
      setupFormRef.value?.setGeneralError(t('register.complete.submitError'))
    }
  } finally {
    loading.value = false
  }
}

const handleOAuthCallback = async () => {
  try {
    const accessToken = route.query.access_token
    const refreshToken = route.query.refresh_token

    if (accessToken) {
      localStorage.setItem('access_token', accessToken)
    }

    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken)
    }

    const user = await userStore.checkAuthStatus()

    if (user) {
      if (user.profile?.registration_completed) {
        router.push('/chats')
      } else {
        needsSetup.value = true
        userEmail.value = user.email

        const emailParts = user.email.split('@')
        if (emailParts.length > 0) {
          suggestedUsername.value = emailParts[0]
        }

        processing.value = false
      }
    } else {
      error.value = 'Authentication failed'
      processing.value = false
    }
  } catch (err) {
    console.error('OAuth callback error:', err)
    error.value = err.response?.data?.error || 'Authentication failed'
    processing.value = false
  }
}

onMounted(() => {
  handleOAuthCallback()
})
</script>
