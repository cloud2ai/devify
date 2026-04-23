<template>
  <div class="relative">
    <!-- Display Mode -->
    <div v-if="!editing" class="group relative">
      <div class="flex items-start gap-2">
        <div class="flex-1 min-w-0">
          <slot name="display">
            <ul
              v-if="displayValue && displayValue.length > 0"
              class="space-y-2"
            >
              <li
                v-for="(item, index) in displayValue"
                :key="index"
                class="flex items-start gap-2 text-sm text-gray-700"
              >
                <span class="text-primary-600 mt-1 flex-shrink-0">•</span>
                <div
                  class="flex-1 min-w-0 markdown-content prose prose-sm max-w-none"
                >
                  <div v-html="renderMarkdown(item)"></div>
                </div>
              </li>
            </ul>
            <span v-else class="text-gray-400 italic">{{ placeholder }}</span>
          </slot>
        </div>
        <div
          v-if="showEditButton && !disabled"
          class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <BaseButton @click="startEditing" variant="primary" size="sm">
            <svg
              class="w-4 h-4 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            {{ t('common.edit') }}
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Edit Mode -->
    <div v-else class="space-y-1">
      <div
        class="relative bg-blue-50 border-2 border-blue-200 rounded-md"
        style="padding: 0.75rem 1rem"
      >
        <textarea
          ref="textareaRef"
          v-model="localText"
          :rows="rows"
          :placeholder="placeholder"
          class="w-full px-0 py-0 text-sm border-0 focus:outline-none bg-transparent resize-y overflow-auto"
          :class="{ 'border-red-300': error }"
        ></textarea>
        <p v-if="error" class="mt-2 text-xs text-red-600">{{ error }}</p>
        <p v-if="hint && !error" class="mt-1 text-xs text-gray-500">
          {{ hint }}
        </p>
      </div>
      <!-- Save/Cancel Icons - Right bottom below input -->
      <div class="flex items-center justify-end gap-1">
        <div
          class="flex items-center bg-white rounded-md shadow-sm border border-gray-200 overflow-hidden"
        >
          <button
            @click="handleSave"
            type="button"
            :disabled="saving"
            class="p-1.5 pr-2 text-green-600 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed relative"
            :title="t('common.save')"
          >
            <svg
              v-if="!saving"
              class="w-4 h-4"
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
            <svg
              v-else
              class="w-4 h-4 animate-spin"
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
            <div class="absolute right-0 top-0 bottom-0 w-px bg-gray-200"></div>
          </button>
          <button
            @click="cancelEditing"
            type="button"
            :disabled="saving"
            class="p-1.5 pl-2 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :title="t('common.cancel')"
          >
            <svg
              class="w-4 h-4"
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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { marked } from 'marked'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  rows: {
    type: Number,
    default: 8
  },
  disabled: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  showEditButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'save', 'cancel'])

const { t } = useI18n()

const editing = ref(false)
const localText = ref('')
const textareaRef = ref(null)
const originalValue = ref([])

const displayValue = computed(() => {
  return props.modelValue || []
})

const startEditing = () => {
  originalValue.value = [...(props.modelValue || [])]
  localText.value = (props.modelValue || []).join('\n')
  editing.value = true
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.focus()
    }
  })
}

const cancelEditing = () => {
  localText.value = originalValue.value.join('\n')
  editing.value = false
  emit('cancel')
}

const handleSave = () => {
  const lines = localText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
  emit('update:modelValue', lines)
  emit('save', lines)
}

defineExpose({
  startEditing,
  isEditing: () => editing.value
})

watch(
  () => props.saving,
  (newValue) => {
    if (!newValue && editing.value) {
      editing.value = false
    }
  }
)

// Configure marked for markdown rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

const renderMarkdown = (text) => {
  if (!text) return ''
  try {
    return marked.parse(text)
  } catch (error) {
    console.error('Markdown parsing error:', error)
    return `<pre>${text}</pre>`
  }
}
</script>

<style scoped>
.markdown-content :deep(p) {
  @apply mb-0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  @apply mb-0;
}

.markdown-content :deep(code) {
  @apply bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono;
}

.markdown-content :deep(strong) {
  @apply font-semibold text-gray-900;
}

.markdown-content :deep(em) {
  @apply italic;
}
</style>
