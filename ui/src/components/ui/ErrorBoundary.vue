<template>
  <div
    v-if="hasError"
    class="min-h-screen flex items-center justify-center bg-gray-50"
  >
    <div class="max-w-md w-full text-center">
      <div
        class="mx-auto h-24 w-24 bg-red-100 rounded-full flex items-center justify-center"
      >
        <svg
          class="h-12 w-12 text-red-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>

      <h1 class="mt-6 text-3xl font-bold text-gray-900">
        Something went wrong
      </h1>

      <p class="mt-2 text-sm text-gray-500">
        {{ error?.message || 'An unexpected error occurred' }}
      </p>

      <div class="mt-6">
        <BaseButton @click="retry" variant="primary"> Try again </BaseButton>
      </div>
    </div>
  </div>

  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import BaseButton from './BaseButton.vue'

const hasError = ref(false)
const error = ref(null)

onErrorCaptured((err, instance, info) => {
  console.error('Component error:', err)
  console.error('Error info:', info)

  hasError.value = true
  error.value = err

  // Return false to prevent the error from propagating
  return false
})

const retry = () => {
  hasError.value = false
  error.value = null
}
</script>
