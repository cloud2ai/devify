<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 translate-x-full"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-full"
    >
      <div
        v-if="state.show"
        :class="[
          'fixed top-4 right-4 left-4 sm:left-auto max-w-sm',
          'rounded-md border p-3 shadow-lg',
          typeClasses[state.type]
        ]"
        style="z-index: 9999"
        role="alert"
      >
        <div class="flex gap-2">
          <div class="flex-shrink-0 pt-0.5">
            <component :is="iconComponent" :class="iconClasses[state.type]" />
          </div>
          <div class="flex-1 min-w-0">
            <p :class="['text-sm font-medium', textClasses[state.type]]">
              {{ state.message }}
            </p>
          </div>
          <button
            @click="handleClose"
            :class="['flex-shrink-0', closeButtonClasses[state.type]]"
            :title="t('common.close')"
          >
            <svg
              class="h-4 w-4"
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
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'

const { t } = useI18n()
const { state, hide } = useToast()

const typeClasses = {
  success: 'bg-green-50 border-green-200',
  error: 'bg-red-50 border-red-200',
  warning: 'bg-yellow-50 border-yellow-200',
  info: 'bg-blue-50 border-blue-200'
}

const textClasses = {
  success: 'text-green-800',
  error: 'text-red-800',
  warning: 'text-yellow-800',
  info: 'text-blue-800'
}

const iconClasses = {
  success: 'h-4 w-4 text-green-400',
  error: 'h-4 w-4 text-red-400',
  warning: 'h-4 w-4 text-yellow-400',
  info: 'h-4 w-4 text-blue-400'
}

const closeButtonClasses = {
  success: 'text-green-400 hover:text-green-600',
  error: 'text-red-400 hover:text-red-600',
  warning: 'text-yellow-400 hover:text-yellow-600',
  info: 'text-blue-400 hover:text-blue-600'
}

const SuccessIcon = (props) =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      d: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z',
      'clip-rule': 'evenodd'
    })
  ])

const ErrorIcon = (props) =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      d: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
      'clip-rule': 'evenodd'
    })
  ])

const WarningIcon = (props) =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      d: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
      'clip-rule': 'evenodd'
    })
  ])

const InfoIcon = (props) =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      d: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z',
      'clip-rule': 'evenodd'
    })
  ])

const iconComponent = computed(() => {
  const icons = {
    success: SuccessIcon,
    error: ErrorIcon,
    warning: WarningIcon,
    info: InfoIcon
  }
  return icons[state.type] || InfoIcon
})

const handleClose = () => {
  hide()
}
</script>
