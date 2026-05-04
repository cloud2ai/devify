<template>
  <span
    class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="badgeClass"
    :title="badgeTitle"
    :aria-label="badgeTitle"
  >
    <svg
      v-if="iconType === 'original'"
      class="h-3 w-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z"
      />
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M14 3v5h5"
      />
    </svg>
    <svg
      v-else-if="iconType === 'canonical'"
      class="h-3 w-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M7 7h3a2 2 0 012 2v2m5-4h-3a2 2 0 00-2 2v2M12 11v6"
      />
      <circle cx="7" cy="7" r="1.5" fill="currentColor" />
      <circle cx="17" cy="7" r="1.5" fill="currentColor" />
      <circle cx="12" cy="17" r="1.5" fill="currentColor" />
    </svg>
    <svg
      v-else-if="iconType === 'merged_source'"
      class="h-3 w-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M8 7h4a4 4 0 014 4v1m0 0l-3-3m3 3l3-3M6 17h8"
      />
    </svg>
    <svg
      v-else-if="iconType === 'merged_again'"
      class="h-3 w-3 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M4 12a8 8 0 0114.65-4.5M20 12a8 8 0 01-14.65 4.5M16 4v4h4"
      />
    </svg>
    <span v-if="showLabel">{{ badgeLabel }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  state: {
    type: String,
    default: 'original'
  },
  showLabel: {
    type: Boolean,
    default: true
  }
})

const { t } = useI18n()

const classMap = {
  original: 'border-slate-200 bg-slate-50 text-slate-700',
  canonical: 'border-amber-200 bg-amber-50 text-amber-700',
  merged_source: 'border-sky-200 bg-sky-50 text-sky-700',
  merged_again: 'border-violet-200 bg-violet-50 text-violet-700'
}

const iconMap = {
  original: 'original',
  canonical: 'canonical',
  merged_source: 'merged_source',
  merged_again: 'merged_again'
}

const badgeLabel = computed(() => {
  const labels = {
    original: t('chats.merge.state.original'),
    canonical: t('chats.merge.state.canonical'),
    merged_source: t('chats.merge.state.mergedSource'),
    merged_again: t('chats.merge.state.mergedAgain')
  }
  return labels[props.state] || labels.original
})

const badgeTitle = computed(() => {
  const titles = {
    original: t('chats.merge.stateTitle.original'),
    canonical: t('chats.merge.stateTitle.canonical'),
    merged_source: t('chats.merge.stateTitle.mergedSource'),
    merged_again: t('chats.merge.stateTitle.mergedAgain')
  }
  return titles[props.state] || titles.original
})

const badgeClass = computed(() => classMap[props.state] || classMap.original)
const iconType = computed(() => iconMap[props.state] || iconMap.original)
</script>
