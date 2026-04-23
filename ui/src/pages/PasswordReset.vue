<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8"
  >
    <div class="max-w-md w-full space-y-8">
      <!-- Header -->
      <div>
        <div class="flex items-center justify-center">
          <h2 class="text-3xl font-extrabold text-gray-900">
            {{ t('password.reset.title') }}
          </h2>
          <div class="ml-3">
            <LanguageSwitcher />
          </div>
        </div>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ t('password.reset.subtitle') }}
        </p>
      </div>

      <!-- Success Message -->
      <div
        v-if="isSuccess"
        class="rounded-md bg-green-50 border border-green-200 p-4"
      >
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="h-5 w-5 text-green-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-green-800">
              {{ t('password.reset.successTitle') }}
            </h3>
            <div class="mt-2 text-sm text-green-700">
              <p>{{ t('password.reset.successMessage') }}</p>
            </div>
            <div class="mt-4">
              <router-link
                to="/login"
                class="text-sm font-medium text-green-600 hover:text-green-500"
              >
                {{ t('password.reset.backToLogin') }} →
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div
        v-else-if="errorMessage"
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
              {{ t('password.reset.error') }}
            </h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ errorMessage }}</p>
            </div>
            <div class="mt-4">
              <router-link
                to="/login"
                class="text-sm font-medium text-red-600 hover:text-red-500"
              >
                {{ t('password.reset.backToLogin') }} →
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Password Reset Form -->
      <form v-else @submit.prevent="handleSubmit" class="mt-8 space-y-6">
        <div class="space-y-4">
          <BaseInput
            v-model="formData.new_password1"
            :label="t('password.reset.newPassword')"
            type="password"
            name="new_password1"
            autocomplete="new-password"
            :placeholder="t('password.reset.newPasswordPlaceholder')"
            required
            :error="errors.new_password1"
            :disabled="loading"
          />

          <BaseInput
            v-model="formData.new_password2"
            :label="t('password.reset.confirmPassword')"
            type="password"
            name="new_password2"
            autocomplete="new-password"
            :placeholder="t('password.reset.confirmPasswordPlaceholder')"
            required
            :error="errors.new_password2"
            :disabled="loading"
          />
        </div>

        <!-- Password Requirements -->
        <div class="text-sm text-gray-600">
          <p class="mb-2 font-medium">{{ t('password.reset.requirements') }}</p>
          <ul class="list-disc list-inside space-y-1 text-xs">
            <li>{{ t('password.reset.requirement1') }}</li>
            <li>{{ t('password.reset.requirement2') }}</li>
            <li>{{ t('password.reset.requirement3') }}</li>
          </ul>
        </div>

        <!-- Submit Button -->
        <div>
          <BaseButton
            type="submit"
            variant="primary"
            class="w-full"
            :loading="loading"
            :disabled="loading"
          >
            {{
              loading
                ? t('password.reset.resetting')
                : t('password.reset.submit')
            }}
          </BaseButton>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { confirmPasswordReset } from '@/api/auth'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const uid = ref('')
const token = ref('')
const loading = ref(false)
const isSuccess = ref(false)
const errorMessage = ref('')

const formData = ref({
  new_password1: '',
  new_password2: ''
})

const errors = ref({
  new_password1: '',
  new_password2: ''
})

// Initialize route params safely
onMounted(() => {
  // Safely get route params
  uid.value = route.params.uid || ''
  token.value = route.params.token || ''

  if (!uid.value || !token.value) {
    errorMessage.value = t('password.reset.invalidLink')
  }
})

const handleSubmit = async () => {
  errorMessage.value = ''
  errors.value = { new_password1: '', new_password2: '' }

  // Validate form data exists
  if (
    !formData.value ||
    !formData.value.new_password1 ||
    !formData.value.new_password2
  ) {
    errorMessage.value = t('password.reset.passwordMismatch')
    return
  }

  // Validate uid and token exist
  if (!uid.value || !token.value) {
    errorMessage.value = t('password.reset.invalidLink')
    return
  }

  if (formData.value.new_password1 !== formData.value.new_password2) {
    errorMessage.value = t('password.reset.passwordMismatch')
    return
  }

  if (formData.value.new_password1.length < 8) {
    errorMessage.value = t('password.reset.passwordTooShort')
    return
  }

  if (formData.value.new_password1.length > 32) {
    errorMessage.value = t('password.reset.passwordTooLong')
    return
  }

  const hasLetter = /[a-zA-Z]/.test(formData.value.new_password1)
  const hasNumber = /[0-9]/.test(formData.value.new_password1)

  if (!hasLetter || !hasNumber) {
    errorMessage.value = t('password.reset.passwordRequirements')
    return
  }

  loading.value = true

  try {
    const requestData = {
      uid: uid.value,
      token: token.value,
      newPassword1: formData.value.new_password1,
      newPassword2: formData.value.new_password2
    }

    const response = await confirmPasswordReset(requestData)

    // Handle custom response format: {code: 0, message: 'success', data: {...}}
    const responseData = response.data
    if (responseData?.data?.success || responseData?.success) {
      isSuccess.value = true
    } else {
      errorMessage.value =
        responseData?.data?.error ||
        responseData?.error ||
        t('password.reset.unknownError')
    }
  } catch (error) {
    // Handle custom response format: {code: 400, message: 'failed', data: {...}}
    const responseData = error.response?.data
    if (responseData?.data?.error) {
      errorMessage.value = responseData.data.error
    } else if (
      responseData?.data?.success === false &&
      responseData?.data?.error
    ) {
      errorMessage.value = responseData.data.error
    } else if (responseData?.error) {
      errorMessage.value = responseData.error
    } else if (responseData?.errors) {
      const errors = responseData.errors
      errorMessage.value = Object.values(errors).flat().join(', ')
    } else if (responseData?.detail) {
      errorMessage.value = responseData.detail
    } else if (responseData?.message) {
      errorMessage.value = responseData.message
    } else {
      errorMessage.value = t('password.reset.unknownError')
    }
  } finally {
    loading.value = false
  }
}
</script>
