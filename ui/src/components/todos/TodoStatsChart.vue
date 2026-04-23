<template>
  <BaseCard v-if="stats">
    <div class="p-3">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-gray-700">
          {{ t('todos.stats.title') }}
        </span>
        <span class="text-sm font-semibold text-gray-900">
          {{ stats.completed }} / {{ stats.total }}
        </span>
      </div>

      <!-- Progress Bar -->
      <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
        <div
          class="h-1.5 rounded-full transition-all"
          :class="completionColorClass"
          :style="{ width: `${completionRate}%` }"
        />
      </div>

      <!-- Stats Details -->
      <div class="flex items-center justify-between text-xs">
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-1">
            <div class="w-2 h-2 rounded-full bg-green-600"></div>
            <span class="text-gray-600">
              {{ t('todos.stats.completed') }}: {{ stats.completed }}
            </span>
          </div>
          <div class="flex items-center gap-1">
            <div class="w-2 h-2 rounded-full bg-yellow-600"></div>
            <span class="text-gray-600">
              {{ t('todos.stats.incomplete') }}: {{ stats.incomplete }}
            </span>
          </div>
        </div>
        <span class="font-medium" :class="completionRateTextColor">
          {{ completionRate }}%
        </span>
      </div>
    </div>
  </BaseCard>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseCard from '@/components/ui/BaseCard.vue'

const props = defineProps({
  stats: {
    type: Object,
    default: null
  }
})

const { t } = useI18n()

const completionRate = computed(() => {
  if (!props.stats || props.stats.total === 0) return 0
  return Math.round((props.stats.completed / props.stats.total) * 100)
})

const completionColorClass = computed(() => {
  const rate = completionRate.value
  if (rate >= 80) return 'bg-green-600'
  if (rate >= 50) return 'bg-primary-600'
  if (rate >= 25) return 'bg-yellow-600'
  return 'bg-red-600'
})

const completionRateTextColor = computed(() => {
  const rate = completionRate.value
  if (rate >= 80) return 'text-green-600'
  if (rate >= 50) return 'text-primary-600'
  if (rate >= 25) return 'text-yellow-600'
  return 'text-red-600'
})
</script>
