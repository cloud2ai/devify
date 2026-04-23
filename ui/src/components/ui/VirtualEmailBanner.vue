<template>
  <div
    v-if="virtualEmail"
    class="bg-blue-50 border border-blue-200 rounded-lg p-2.5 sm:p-3 mb-4"
  >
    <div class="flex items-center justify-between gap-2 sm:gap-3">
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <div class="flex-shrink-0">
          <svg
            class="h-4 w-4 sm:h-5 sm:w-5 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        </div>

        <div class="min-w-0 flex-1">
          <div
            class="flex flex-col sm:flex-row sm:items-center gap-0.5 sm:gap-1.5"
          >
            <span class="text-xs font-medium text-blue-800 shrink-0">
              {{ label }}:
            </span>
            <code
              class="text-xs sm:text-sm font-mono font-medium text-blue-900 truncate block"
              :title="virtualEmail"
            >
              {{ virtualEmail }}
            </code>
          </div>
        </div>
      </div>

      <button
        @click="copyEmail"
        class="flex-shrink-0 inline-flex items-center gap-1 text-xs font-medium text-blue-700 hover:text-blue-900 bg-blue-100 hover:bg-blue-200 px-2 py-1 rounded transition-colors"
        :title="t('settings.copyEmail')"
      >
        <svg
          v-if="!copied"
          class="h-3.5 w-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
        <svg
          v-else
          class="h-3.5 w-3.5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 13l4 4L19 7"
          />
        </svg>
        <span class="hidden sm:inline">
          {{ copied ? t('common.copied') : t('common.copy') }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  virtualEmail: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  }
})

const { t } = useI18n()

const copied = ref(false)

const copyEmail = async () => {
  if (!props.virtualEmail) return

  try {
    await navigator.clipboard.writeText(props.virtualEmail)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy email:', error)
  }
}
</script>
