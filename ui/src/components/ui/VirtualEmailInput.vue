<template>
  <div class="virtual-email-input">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
    </label>

    <div class="mt-1">
      <div class="flex rounded-md shadow-sm">
        <div class="relative flex-1">
          <input
            v-model="username"
            type="text"
            @input="handleInput"
            @blur="handleBlur"
            :placeholder="placeholder"
            class="input rounded-r-none pr-10"
            :class="{
              'input-error': error,
              'border-green-500': isValid && username
            }"
            :disabled="disabled"
          />
          <div
            class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
          >
            <svg
              v-if="checking"
              class="animate-spin h-5 w-5 text-gray-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <svg
              v-else-if="isValid && username"
              class="h-5 w-5 text-green-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
            <svg
              v-else-if="error"
              class="h-5 w-5 text-red-500"
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
        </div>
        <span
          class="inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 text-sm"
        >
          @{{ domain }}
        </span>
      </div>
    </div>

    <p v-if="helpText && !error" class="mt-1 text-sm text-gray-500">
      {{ helpText }}
    </p>

    <p v-if="error" class="mt-1 text-sm text-red-600">
      {{ error }}
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { checkUsernameAvailability } from '@/api/auth'
import { useDebounce } from '@/composables/useDebounce'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  helpText: {
    type: String,
    default: ''
  },
  domain: {
    type: String,
    default: 'devify.local'
  },
  error: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'validation'])

const { t } = useI18n()

const username = ref(props.modelValue)
const checking = ref(false)
const isValid = ref(false)
const validationError = ref('')

const fullEmail = computed(() => {
  return `${username.value}@${props.domain}`
})

const generateUsernameSuggestions = (baseUsername) => {
  const suggestions = []
  const randomNum1 = Math.floor(Math.random() * 100)
  const randomNum2 = Math.floor(Math.random() * 1000)
  const year = new Date().getFullYear().toString().slice(-2)

  suggestions.push(`${baseUsername}${randomNum1}`)
  suggestions.push(`${baseUsername}${year}`)
  suggestions.push(`${baseUsername}${randomNum2}`)

  return suggestions.slice(0, 3)
}

const translateErrorMessage = (message, currentUsername) => {
  const errorMap = {
    'This username is reserved and cannot be used': t('auth.usernameReserved'),
    'Username can only contain letters, numbers, dots, hyphens, and underscores':
      t('auth.usernameInvalidChars'),
    'Username cannot start or end with a dot': t('auth.usernameInvalidDot')
  }

  if (message === 'This username is already taken') {
    const suggestions = generateUsernameSuggestions(currentUsername)
    return t('auth.usernameNotAvailableWithSuggestions', {
      suggestions: suggestions.join(', ')
    })
  }

  return errorMap[message] || message
}

const checkUsername = async (value) => {
  if (!value || value.length < 3) {
    validationError.value = t('auth.usernameTooShort')
    isValid.value = false
    emit('validation', { valid: false, error: validationError.value })
    return
  }

  checking.value = true
  try {
    const response = await checkUsernameAvailability(value)

    const responseData = response.data.data || response.data

    if (responseData.available) {
      isValid.value = true
      validationError.value = ''
      emit('validation', { valid: true, error: '' })
    } else {
      isValid.value = false
      const translatedMessage = translateErrorMessage(
        responseData.message,
        value
      )
      validationError.value =
        translatedMessage || t('auth.usernameNotAvailable')
      emit('validation', { valid: false, error: validationError.value })
    }
  } catch (error) {
    console.error('Failed to check username:', error)
    isValid.value = false
    validationError.value = t('auth.usernameCheckFailed')
    emit('validation', { valid: false, error: validationError.value })
  } finally {
    checking.value = false
  }
}

const { debouncedFn: debouncedCheck } = useDebounce(checkUsername, 500)

const handleInput = () => {
  emit('update:modelValue', username.value)

  if (username.value) {
    isValid.value = false
    validationError.value = ''
    debouncedCheck(username.value)
  } else {
    isValid.value = false
    validationError.value = ''
    emit('validation', { valid: false, error: '' })
  }
}

const handleBlur = () => {
  if (
    username.value &&
    !isValid.value &&
    !checking.value &&
    !validationError.value
  ) {
    debouncedCheck(username.value)
  }
}

watch(
  () => props.modelValue,
  (newValue, oldValue) => {
    username.value = newValue

    // Auto-validate immediately when modelValue is set from parent
    // No debounce needed since it's not user typing
    if (newValue && newValue.length >= 3 && newValue !== oldValue) {
      checkUsername(newValue)
    }
  },
  { immediate: true }
)

watch(
  () => props.error,
  (newError) => {
    if (newError) {
      validationError.value = newError
      isValid.value = false
    }
  }
)
</script>

<style scoped>
.virtual-email-input {
  width: 100%;
}
</style>
