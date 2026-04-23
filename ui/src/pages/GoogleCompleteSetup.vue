<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8"
  >
    <div class="max-w-md w-full space-y-8">
      <div>
        <div class="flex items-center justify-center">
          <h2 class="text-3xl font-extrabold text-gray-900">
            {{ t('register.google.completeTitle') }}
          </h2>
          <div class="ml-3">
            <LanguageSwitcher />
          </div>
        </div>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ t('register.google.completeSubtitle') }}
        </p>
      </div>

      <div>
        <UserSetupForm
          ref="setupFormRef"
          :display-email="userEmail"
          :email-label="t('register.google.loggedInAs')"
          :initial-username="suggestedUsername"
          :loading="loading"
          :require-password="false"
          @submit="handleComplete"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/store/user'
import { completeGoogleSetup } from '@/api/auth'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import UserSetupForm from '@/components/ui/UserSetupForm.vue'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const userEmail = ref('')
const suggestedUsername = ref('')
const setupFormRef = ref(null)

const handleComplete = async (formValues) => {
  loading.value = true

  try {
    const response = await completeGoogleSetup({
      virtual_email_username: formValues.virtualEmailUsername,
      scene: formValues.scene,
      language: formValues.language,
      timezone: formValues.timezone
    })

    const responseData = response.data.data || response.data

    if (responseData.success || response.data.code === 0) {
      // Update token if provided in response
      if (responseData.access) {
        userStore.setToken(responseData.access, responseData.refresh)
      }

      // Update user info directly from response if available
      // The response now includes full user info with virtual_email from UserDetailsSerializer
      if (responseData.user) {
        userStore.setUser(responseData.user)
        // Load preferences to sync language and timezone settings
        await userStore.loadUserPreferences()
      } else {
        // Fallback: refresh user info if not in response
        await userStore.checkAuth()
      }

      // Wait for next tick to ensure all reactive updates are complete
      await nextTick()

      router.push('/chats')
    }
  } catch (error) {
    console.error('Google setup completion error:', error)

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

onMounted(async () => {
  try {
    const isAuthenticated = await userStore.checkAuth()

    if (isAuthenticated && userStore.user) {
      userEmail.value = userStore.user.email

      const emailParts = userStore.user.email.split('@')
      if (emailParts.length > 0) {
        suggestedUsername.value = emailParts[0]
      }

      if (userStore.user.profile?.registration_completed) {
        router.push('/chats')
      }
    } else {
      router.push('/login')
    }
  } catch (err) {
    console.error('Failed to load user:', err)
    router.push('/login')
  }
})
</script>
