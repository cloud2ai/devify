<template>
  <div :class="containerClasses">
    <div :class="spinnerClasses"></div>
    <p v-if="showText" :class="textClasses">
      {{ text || t('common.loading') }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary'].includes(value)
  },
  fullPage: {
    type: Boolean,
    default: false
  },
  showText: {
    type: Boolean,
    default: true
  },
  text: {
    type: String,
    default: ''
  },
  inline: {
    type: Boolean,
    default: false
  }
})

const { t } = useI18n()

const containerClasses = computed(() => {
  const base = props.fullPage
    ? 'flex flex-col items-center justify-center py-12'
    : 'py-8 text-center'
  return base
})

const spinnerClasses = computed(() => {
  const sizeClasses = {
    sm: 'h-6 w-6',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }
  const colorClasses = {
    default: 'border-gray-900',
    primary: 'border-primary-600'
  }
  return `inline-block animate-spin rounded-full border-b-2 ${sizeClasses[props.size]} ${colorClasses[props.variant]}`
})

const textClasses = computed(() => {
  const sizeText = props.size === 'lg' ? 'text-sm' : 'text-xs'
  const marginTop = props.fullPage ? 'mt-4' : 'mt-2'
  return `${marginTop} ${sizeText} text-gray-600`
})
</script>
