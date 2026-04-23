<template>
  <span
    :class="getStatusClass(status)"
    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
  >
    <!-- Success icon -->
    <svg
      v-if="status === 'success'"
      class="w-3 h-3 flex-shrink-0"
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
    <!-- Failed icon -->
    <svg
      v-else-if="status === 'failed'"
      class="w-3 h-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
    <!-- Processing icon (spinning) -->
    <svg
      v-else-if="status === 'processing'"
      class="animate-spin w-3 h-3 flex-shrink-0"
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
    <!-- Fetched icon (clock) -->
    <svg
      v-else-if="status === 'fetched'"
      class="w-3 h-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
    <!-- Unknown status icon -->
    <svg
      v-else
      class="w-3 h-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
    {{ getStatusText(status) }}
  </span>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  status: {
    type: String,
    default: 'unknown'
  }
})

const getStatusClass = (status) => {
  const classes = {
    success: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
    processing: 'bg-yellow-50 text-yellow-700',
    fetched: 'bg-blue-50 text-blue-700',
    pending: 'bg-yellow-50 text-yellow-700',
    completed: 'bg-green-50 text-green-700'
  }
  return classes[status] || 'bg-gray-50 text-gray-700'
}

const getStatusText = (status) => {
  const statusTexts = {
    success: t('common.status.success'),
    failed: t('common.status.failed'),
    processing: t('common.status.processing'),
    fetched: t('common.status.fetched'),
    pending: t('common.status.pending'),
    completed: t('common.status.completed')
  }
  return statusTexts[status] || status || t('common.status.unknown')
}
</script>
