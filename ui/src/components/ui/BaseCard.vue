<template>
  <div :class="cardClasses">
    <div v-if="$slots.header || title" :class="headerClasses">
      <slot name="header">
        <h3 v-if="title" class="text-lg font-semibold text-gray-900">
          {{ title }}
        </h3>
      </slot>
    </div>

    <div class="card-body">
      <slot />
    </div>

    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  padding: {
    type: String,
    default: 'default',
    validator: (value) => ['none', 'sm', 'default', 'lg'].includes(value)
  },
  shadow: {
    type: String,
    default: 'sm',
    validator: (value) => ['none', 'sm', 'md', 'lg'].includes(value)
  },
  headerMuted: {
    type: Boolean,
    default: false
  },
  headerClass: {
    type: String,
    default: ''
  }
})

const cardClasses = computed(() => {
  const baseClasses = 'card'
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    default: '',
    lg: 'p-8'
  }
  const shadowClasses = {
    none: 'shadow-none',
    sm: 'shadow-sm',
    md: 'shadow-md',
    lg: 'shadow-lg'
  }

  return [
    baseClasses,
    paddingClasses[props.padding],
    shadowClasses[props.shadow]
  ]
    .filter(Boolean)
    .join(' ')
})

const headerClasses = computed(() => {
  const base = 'card-header'
  const muted = props.headerMuted
    ? 'bg-gray-50 border-b border-gray-100 px-4 py-3'
    : ''
  return [base, muted, props.headerClass].filter(Boolean).join(' ')
})
</script>
