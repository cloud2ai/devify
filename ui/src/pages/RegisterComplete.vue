<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8"
  >
    <div class="max-w-md w-full space-y-8">
      <div>
        <div class="flex items-center justify-center">
          <h2 class="text-3xl font-extrabold text-gray-900">
            {{ t('register.complete.title') }}
          </h2>
          <div class="ml-3">
            <LanguageSwitcher />
          </div>
        </div>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ t('register.complete.subtitle') }}
        </p>
      </div>

      <div v-if="verifying" class="text-center py-12">
        <div
          class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"
        ></div>
        <p class="mt-4 text-gray-600">{{ t('register.complete.verifying') }}</p>
      </div>

      <div
        v-else-if="tokenInvalid"
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
              {{ t('register.complete.invalidToken') }}
            </h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ t('register.complete.invalidTokenMessage') }}</p>
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

      <div v-else>
        <UserSetupForm
          ref="setupFormRef"
          :display-email="userEmail"
          :email-label="t('register.complete.registeringFor')"
          :initial-username="suggestedUsername"
          :loading="loading"
          @submit="handleComplete"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/user'
import { verifyRegistrationToken, completeRegistration } from '@/api/auth'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import UserSetupForm from '@/components/ui/UserSetupForm.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const token = ref(route.params.token)
const verifying = ref(true)
const tokenInvalid = ref(false)
const userEmail = ref('')
const suggestedUsername = ref('')
const loading = ref(false)
const setupFormRef = ref(null)

const verifyToken = async () => {
  try {
    const response = await verifyRegistrationToken(token.value)

    const responseData = response.data.data || response.data

    if (responseData.valid) {
      userEmail.value = responseData.email

      const emailParts = responseData.email.split('@')
      if (emailParts.length > 0) {
        suggestedUsername.value = emailParts[0]
      }

      verifying.value = false
    } else {
      tokenInvalid.value = true
      verifying.value = false
    }
  } catch (error) {
    console.error('Token verification error:', error)
    tokenInvalid.value = true
    verifying.value = false
  }
}

const handleComplete = async (formValues) => {
  loading.value = true

  try {
    const response = await completeRegistration({
      token: token.value,
      password: formValues.password,
      virtual_email_username: formValues.virtualEmailUsername,
      scene: formValues.scene,
      language: formValues.language,
      timezone: formValues.timezone
    })

    const responseData = response.data.data || response.data

    if (responseData.success || responseData.access) {
      if (responseData.access) {
        userStore.token = responseData.access
        localStorage.setItem('access_token', responseData.access)
      }

      if (responseData.refresh) {
        localStorage.setItem('refresh_token', responseData.refresh)
      }

      // Always refresh full profile to include generated fields
      // like virtual_email and auth_info
      await userStore.checkAuth()

      router.push('/chats')
    }
  } catch (error) {
    console.error('Registration completion error:', error)

    const errorData = error.response?.data?.data || error.response?.data

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

onMounted(() => {
  if (!token.value) {
    tokenInvalid.value = true
    verifying.value = false
  } else {
    verifyToken()
  }
})
</script>
