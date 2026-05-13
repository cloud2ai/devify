<template>
  <span
    class="inline-flex items-center gap-1 rounded-full border whitespace-nowrap font-medium"
    :class="[badgeClass, sizeClass]"
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
    <span v-if="showLabel" class="truncate">{{ badgeLabel }}</span>
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
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md'].includes(value)
  }
})

const { t } = useI18n()

const classMap = {
  original: 'border-slate-200 bg-slate-50 text-slate-700',
  canonical: 'border-amber-200 bg-amber-50 text-amber-700'
}

const sizeMap = {
  sm: 'px-1.5 py-0.5 text-[11px] leading-none',
  md: 'px-2 py-0.5 text-xs'
}

const iconMap = {
  original: 'original',
  canonical: 'canonical'
}

const badgeLabel = computed(() => {
  const labels = {
    original: t('chats.merge.state.original'),
    canonical: t('chats.merge.state.canonical')
  }
  return labels[props.state] || labels.original
})

const badgeTitle = computed(() => {
  const titles = {
    original: t('chats.merge.stateTitle.original'),
    canonical: t('chats.merge.stateTitle.canonical')
  }
  return titles[props.state] || titles.original
})

const badgeClass = computed(() => classMap[props.state] || classMap.original)
const iconType = computed(() => iconMap[props.state] || iconMap.original)
const sizeClass = computed(() => sizeMap[props.size] || sizeMap.md)
</script>
