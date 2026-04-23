<template>
  <span class="inline-flex items-center gap-2">
    <span
      class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md text-white"
      :style="fallbackStyle"
      :class="sizeClass"
    >
      <img
        v-if="iconUrl && !imgFailed"
        :src="iconUrl"
        :alt="provider"
        class="h-full w-full object-contain"
        :class="sizeClass"
        @error="onImgError"
      />
      <span
        v-else
        class="flex h-full w-full items-center justify-center font-semibold leading-none"
        :class="letterClass"
      >
        {{ fallbackLetter }}
      </span>
    </span>
    <slot />
  </span>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  getProviderColor,
  getProviderFallbackLetter,
  getProviderIconUrl
} from './providerIcons.js'

const props = defineProps({
  provider: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md'
  }
})

const imgFailed = ref(false)

const iconUrl = computed(() => {
  if (imgFailed.value || !props.provider) return null
  return getProviderIconUrl(props.provider)
})

const fallbackLetter = computed(() => getProviderFallbackLetter(props.provider))

const fallbackStyle = computed(() => ({
  backgroundColor: iconUrl.value
    ? 'transparent'
    : getProviderColor(props.provider)
}))

const sizeClass = computed(() => {
  const s = props.size
  if (s === 'sm') return 'h-5 w-5'
  if (s === 'lg') return 'h-8 w-8'
  return 'h-6 w-6'
})

const letterClass = computed(() => {
  const s = props.size
  if (s === 'sm') return 'text-xs'
  if (s === 'lg') return 'text-sm'
  return 'text-xs'
})

function onImgError() {
  imgFailed.value = true
}
</script>
