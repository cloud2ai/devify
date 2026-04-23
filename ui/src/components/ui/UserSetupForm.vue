<template>
  <div class="space-y-6">
    <div
      v-if="displayEmail"
      class="bg-blue-50 border border-blue-200 rounded-lg p-4"
    >
      <p class="text-sm text-blue-800">
        <span class="font-medium">{{ emailLabel }}:</span>
        {{ displayEmail }}
      </p>
    </div>

    <div class="space-y-4">
      <VirtualEmailInput
        v-model="formData.virtualEmailUsername"
        :label="t('register.virtualEmail.label')"
        :placeholder="t('register.virtualEmail.placeholder')"
        :help-text="t('register.virtualEmail.info')"
        :domain="emailDomain"
        :error="errors.virtualEmailUsername"
        @validation="handleUsernameValidation"
      />

      <template v-if="requirePassword">
        <BaseInput
          v-model="formData.password"
          :label="t('auth.password')"
          type="password"
          name="password"
          autocomplete="new-password"
          :placeholder="t('register.complete.passwordPlaceholder')"
          :help="
            !errors.password && !passwordTouched
              ? t('auth.passwordHelpComplex')
              : ''
          "
          required
          :error="errors.password"
          :valid="isPasswordValid"
          :show-validation-icon="passwordTouched"
          @input="handlePasswordInput"
          @blur="validatePassword"
        />

        <BaseInput
          v-model="formData.confirmPassword"
          :label="t('auth.confirmPassword')"
          type="password"
          name="confirmPassword"
          autocomplete="new-password"
          :placeholder="t('auth.confirmPassword')"
          required
          :error="errors.confirmPassword"
          :valid="isConfirmPasswordValid"
          :show-validation-icon="confirmPasswordTouched"
          @input="handleConfirmPasswordInput"
          @blur="validateConfirmPassword"
        />
      </template>

      <SceneSelector
        v-model="formData.scene"
        :label="t('register.scene.label')"
        :error="errors.scene"
      />

      <div class="border-t border-gray-200 pt-4">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          <svg
            :class="{ 'rotate-90': showAdvanced }"
            class="w-4 h-4 mr-1 transition-transform"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
              clip-rule="evenodd"
            />
          </svg>
          {{ t('settings.advancedOptions') || '高级选项' }}
        </button>

        <div v-if="showAdvanced" class="mt-4 space-y-4 pl-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ t('settings.language') }}
            </label>
            <select v-model="formData.language" class="input w-full">
              <option
                v-for="opt in languageOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
            <p class="mt-1 text-xs text-gray-500">
              {{ t('settings.detectedText') }}:
              {{ getFriendlyLanguageName(detectedLanguage) }}
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              {{ t('settings.timezone') }}
            </label>
            <div
              class="input w-full bg-gray-50 text-gray-600 cursor-not-allowed"
            >
              {{ getFriendlyTimezoneName(detectedTimezone) }}
            </div>
            <p class="mt-1 text-xs text-gray-500">
              {{ t('settings.autoDetected') }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="rounded-md bg-red-50 border border-red-200 p-4"
    >
      <p class="text-sm text-red-700">
        {{ errorMessage }}
      </p>
    </div>

    <BaseButton
      type="button"
      variant="primary"
      class="w-full"
      :loading="loading"
      :disabled="loading || !isFormValid"
      @click="handleSubmit"
    >
      {{
        loading
          ? t('register.complete.submitting')
          : t('register.complete.submit')
      }}
    </BaseButton>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  detectTimezone,
  detectLanguage,
  getFriendlyLanguageName,
  getFriendlyTimezoneName
} from '@/utils/timezone'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import VirtualEmailInput from '@/components/ui/VirtualEmailInput.vue'
import SceneSelector from '@/components/ui/SceneSelector.vue'

// Get email domain from environment variable
const emailDomain = import.meta.env.VITE_EMAIL_DOMAIN || 'devify.local'

const props = defineProps({
  displayEmail: {
    type: String,
    default: ''
  },
  emailLabel: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  initialUsername: {
    type: String,
    default: ''
  },
  requirePassword: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['submit'])

const { t, locale } = useI18n()

const detectedTimezone = ref(detectTimezone())
const detectedLanguage = ref(detectLanguage())

const formData = ref({
  virtualEmailUsername: props.initialUsername || '',
  password: '',
  confirmPassword: '',
  scene: '',
  language: detectedLanguage.value,
  timezone: detectedTimezone.value
})

const errors = ref({
  virtualEmailUsername: '',
  password: '',
  confirmPassword: '',
  scene: ''
})

const errorMessage = ref('')
const usernameValid = ref(false)
const showAdvanced = ref(false)

const languageOptions = computed(() => {
  const codes = ['zh-CN', 'en', 'es']
  return codes.map((code) => ({
    value: code,
    label:
      code === 'en'
        ? t('settings.languages.en')
        : code === 'zh-CN'
          ? t('settings.languages.zh-CN')
          : t('settings.languages.es')
  }))
})

// Note: Keep form language independent from global UI language.
// Users can choose a different registration language without
// affecting or being affected by the current UI locale.

const passwordTouched = ref(false)
const confirmPasswordTouched = ref(false)

const isPasswordValid = computed(() => {
  return (
    passwordTouched.value &&
    formData.value.password &&
    formData.value.password.length >= 8 &&
    !errors.value.password
  )
})

const isConfirmPasswordValid = computed(() => {
  return (
    confirmPasswordTouched.value &&
    formData.value.confirmPassword &&
    formData.value.password === formData.value.confirmPassword &&
    !errors.value.confirmPassword
  )
})

const isFormValid = computed(() => {
  const baseValid =
    formData.value.virtualEmailUsername &&
    formData.value.scene &&
    formData.value.language &&
    formData.value.timezone &&
    usernameValid.value &&
    !Object.values(errors.value).some((error) => error)

  if (props.requirePassword) {
    return (
      baseValid &&
      formData.value.password &&
      formData.value.confirmPassword &&
      formData.value.password === formData.value.confirmPassword
    )
  }

  return baseValid
})

const handleUsernameValidation = (validation) => {
  usernameValid.value = validation.valid
  if (!validation.valid && validation.error) {
    errors.value.virtualEmailUsername = validation.error
  } else {
    errors.value.virtualEmailUsername = ''
  }
}

const validatePasswordComplexity = (password) => {
  const hasLetter = /[a-zA-Z]/.test(password)
  const hasNumber = /[0-9]/.test(password)
  return hasLetter && hasNumber
}

const handlePasswordInput = () => {
  passwordTouched.value = true

  if (passwordTouched.value && formData.value.password) {
    errors.value.password = ''
    const pwd = formData.value.password

    if (pwd.length < 8) {
      errors.value.password = t('auth.invalid.passwordTooShort')
    } else if (pwd.length > 32) {
      errors.value.password = t('auth.invalid.passwordTooLong')
    } else if (!validatePasswordComplexity(pwd)) {
      errors.value.password = t('auth.invalid.passwordComplexity')
    }
  }

  if (confirmPasswordTouched.value && formData.value.confirmPassword) {
    validateConfirmPassword()
  }
}

const handleConfirmPasswordInput = () => {
  confirmPasswordTouched.value = true

  if (confirmPasswordTouched.value && formData.value.confirmPassword) {
    errors.value.confirmPassword = ''

    if (formData.value.password !== formData.value.confirmPassword) {
      errors.value.confirmPassword = t('auth.invalid.passwordMatch')
    }
  }
}

const validatePassword = () => {
  passwordTouched.value = true
  errors.value.password = ''

  if (!formData.value.password) {
    errors.value.password = t('auth.required.password')
    return false
  }

  const pwd = formData.value.password

  if (pwd.length < 8) {
    errors.value.password = t('auth.invalid.passwordTooShort')
    return false
  }

  if (pwd.length > 32) {
    errors.value.password = t('auth.invalid.passwordTooLong')
    return false
  }

  if (!validatePasswordComplexity(pwd)) {
    errors.value.password = t('auth.invalid.passwordComplexity')
    return false
  }

  return true
}

const validateConfirmPassword = () => {
  confirmPasswordTouched.value = true
  errors.value.confirmPassword = ''

  if (!formData.value.confirmPassword) {
    errors.value.confirmPassword = t('auth.required.confirmPassword')
    return false
  }

  if (formData.value.password !== formData.value.confirmPassword) {
    errors.value.confirmPassword = t('auth.invalid.passwordMatch')
    return false
  }

  return true
}

const handleSubmit = (event) => {
  event?.preventDefault()

  if (props.requirePassword) {
    if (!validatePassword() || !validateConfirmPassword()) {
      return
    }
  }

  if (!isFormValid.value) {
    errorMessage.value = t('register.complete.pleaseComplete')
    return
  }

  emit('submit', formData.value)
}

const setError = (field, message) => {
  if (errors.value.hasOwnProperty(field)) {
    errors.value[field] = message
  }
}

const setGeneralError = (message) => {
  errorMessage.value = message
}

watch(
  () => props.initialUsername,
  (newValue) => {
    if (newValue) {
      formData.value.virtualEmailUsername = newValue
    }
  },
  { immediate: true }
)

defineExpose({
  formData,
  setError,
  setGeneralError
})
</script>
