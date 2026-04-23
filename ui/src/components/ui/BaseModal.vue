<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-50 overflow-y-auto"
      @click="handleBackdropClick"
    >
      <div class="flex min-h-full items-center justify-center p-4">
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          aria-hidden="true"
        />

        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          enter-to-class="opacity-100 translate-y-0 sm:scale-100"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 translate-y-0 sm:scale-100"
          leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
        >
          <div
            v-if="show"
            class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all w-full max-w-lg max-h-[90vh] sm:max-h-[90vh] flex flex-col my-4 sm:my-8"
            @click.stop
          >
            <!-- Header -->
            <div
              class="flex-shrink-0 bg-white px-4 pt-5 pb-3 sm:px-6 sm:pt-6 sm:pb-4 border-b border-gray-200"
            >
              <h3
                v-if="title"
                class="text-base font-semibold leading-6 text-gray-900 text-left"
              >
                {{ title }}
              </h3>
            </div>

            <!-- Scrollable Content -->
            <div
              class="flex-1 overflow-y-auto -webkit-overflow-scrolling-touch min-h-0"
            >
              <div class="bg-white px-4 py-4 sm:px-6 sm:py-4">
                <div v-if="icon" class="sm:flex sm:items-start">
                  <div
                    class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10"
                    :class="iconClasses"
                  >
                    <component :is="icon" class="h-6 w-6" />
                  </div>

                  <div class="mt-3 text-left sm:ml-4 sm:mt-0 w-full">
                    <slot />
                  </div>
                </div>
                <div v-else class="text-left w-full">
                  <slot />
                </div>
              </div>
            </div>

            <!-- Footer (fixed at bottom) -->
            <div
              v-if="$slots.footer"
              class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6 flex-shrink-0 border-t border-gray-200"
            >
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  icon: {
    type: [String, Object],
    default: null
  },
  iconType: {
    type: String,
    default: 'info',
    validator: (value) =>
      ['info', 'success', 'warning', 'error'].includes(value)
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close'])

const iconClasses = computed(() => {
  const typeClasses = {
    info: 'bg-blue-100 text-blue-600',
    success: 'bg-green-100 text-green-600',
    warning: 'bg-yellow-100 text-yellow-600',
    error: 'bg-red-100 text-red-600'
  }

  return typeClasses[props.iconType]
})

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    emit('close')
  }
}
</script>
