<template>
  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-40 bg-gray-900 bg-opacity-50"
      aria-hidden="true"
      @click="$emit('close')"
    />
  </Transition>

  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition-transform duration-250 ease-in"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <div
      v-if="show"
      class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white shadow-2xl"
      role="dialog"
      aria-modal="true"
      :aria-label="t('dataManagement.conversations.filter')"
    >
      <div
        class="flex-shrink-0 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4"
      >
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">
              {{ t('dataManagement.conversations.filter') }}
            </h2>
            <p class="text-xs text-gray-500">
              {{ t('dataManagement.conversations.filterHint') }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            :aria-label="t('common.close')"
            @click="$emit('close')"
          >
            <svg
              class="h-5 w-5"
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

      <div class="flex-1 space-y-5 overflow-y-auto p-6">
        <div class="space-y-2">
          <label class="text-xs font-semibold uppercase text-gray-500">
            {{ t('dataManagement.conversations.userFilter') }}
          </label>
          <select
            v-model="draftFilters.user_id"
            class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">
              {{ t('taskManagement.list.userFilterAll') }}
            </option>
            <option v-for="u in userOptions" :key="u.id" :value="u.id">
              {{ u.label }}
            </option>
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-xs font-semibold uppercase text-gray-500">
            {{ t('dataManagement.conversations.statusFilter') }}
          </label>
          <select
            v-model="draftFilters.status"
            class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">
              {{ t('dataManagement.conversations.statusAll') }}
            </option>
            <option
              v-for="status in statusOptions"
              :key="status.value"
              :value="status.value"
            >
              {{ status.label }}
            </option>
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-xs font-semibold uppercase text-gray-500">
            {{ t('common.dateRange') }}
          </label>
          <div class="flex items-center gap-2">
            <input
              v-model="draftFilters.start_date"
              type="date"
              :max="draftFilters.end_date || undefined"
              class="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <span class="text-gray-400">–</span>
            <input
              v-model="draftFilters.end_date"
              type="date"
              :min="draftFilters.start_date || undefined"
              class="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      <div
        class="flex flex-shrink-0 items-center justify-between gap-3 border-t border-gray-200 px-6 py-4"
      >
        <div class="flex items-center justify-between gap-3">
          <BaseButton variant="outline" @click="$emit('reset')">
            {{ t('common.reset') }}
          </BaseButton>
          <BaseButton variant="primary" @click="$emit('confirm')">
            {{ t('common.confirm') }}
          </BaseButton>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'

defineProps({
  show: {
    type: Boolean,
    default: false
  },
  draftFilters: {
    type: Object,
    required: true
  },
  userOptions: {
    type: Array,
    default: () => []
  }
})

defineEmits(['close', 'reset', 'confirm'])

const { t } = useI18n()

const statusOptions = computed(() => [
  { value: 'fetched', label: t('common.status.fetched') },
  { value: 'processing', label: t('common.status.processing') },
  { value: 'success', label: t('common.status.success') },
  { value: 'failed', label: t('common.status.failed') }
])
</script>
