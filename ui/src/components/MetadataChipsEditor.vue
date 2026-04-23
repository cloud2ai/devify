<template>
  <div
    class="relative flex flex-wrap gap-2"
    :aria-busy="loading ? 'true' : 'false'"
  >
    <template v-if="isArray">
      <!-- Show chips if they exist -->
      <template v-if="chips.length > 0">
        <div
          v-for="(chipIndex, loopIndex) in visibleIndexes"
          :key="`${chipIndex}-${loopIndex}`"
          :class="chipClasses"
        >
          <template v-if="editingIndex === chipIndex">
            <span class="flex items-center gap-1">
              <svg
                v-if="loading"
                class="w-3.5 h-3.5 animate-spin text-gray-500"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  stroke-width="4"
                  d="M4 12a8 8 0 018-8"
                />
              </svg>
              <input
                v-model="inputValue"
                type="text"
                :class="inputClasses"
                @keydown.enter.prevent="handleEnterKey(chipIndex)"
                @keydown.esc.prevent="handleEscKey"
                autofocus
              />
              <button
                @mousedown.prevent="commitEdit(chipIndex)"
                class="text-green-600 hover:text-green-800"
                aria-label="Confirm"
                title="Confirm"
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
                    d="M5 13l4 4L19 7"
                  ></path>
                </svg>
              </button>
              <button
                @mousedown.prevent="cancelEdit"
                class="text-red-600 hover:text-red-800"
                aria-label="Cancel"
                title="Cancel"
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
                  ></path>
                </svg>
              </button>
            </span>
          </template>
          <template v-else>
            <span
              class="select-none inline-flex items-center cursor-pointer"
              @click="startEdit(chipIndex)"
              >{{ chips[chipIndex] }}</span
            >
            <button
              class="ml-1 hover:text-red-600 inline-flex items-center disabled:opacity-50"
              @click.stop="removeChip(chipIndex)"
              :disabled="loading"
              aria-label="Remove"
            >
              <svg
                v-if="loading"
                class="w-3.5 h-3.5 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  stroke-width="4"
                  d="M4 12a8 8 0 018-8"
                />
              </svg>
              <span v-else>×</span>
            </button>
          </template>
        </div>
      </template>
      <div class="flex items-center gap-1">
        <button
          v-if="shouldLimit && chips.length > 0"
          class="inline-flex items-center justify-center h-6 px-2 rounded border text-xs text-gray-600 hover:text-gray-800 hover:border-gray-400"
          @click="showAll = !showAll"
        >
          <template v-if="!showAll">+{{ remainingCount }}</template>
          <template v-else>
            <svg
              class="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
          </template>
        </button>
        <!-- Add button - show only when not editing any item -->
        <button
          v-if="editingIndex === -1"
          :class="addBtnClasses"
          @click="addChip"
          :disabled="loading || props.disabled"
          aria-label="Add"
          title="Add"
        >
          <svg
            v-if="loading"
            class="w-3.5 h-3.5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke-width="4"
            ></circle>
            <path class="opacity-75" stroke-width="4" d="M4 12a8 8 0 018-8" />
          </svg>
          <svg
            v-else
            class="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            ></path>
          </svg>
        </button>
      </div>
    </template>

    <template v-else>
      <!-- Show add button when empty (outside chipClasses div) -->
      <template v-if="isSingleEmpty && editingIndex !== 0">
        <button
          :class="addBtnClasses"
          @click="startEdit(0)"
          :disabled="loading || props.disabled"
          aria-label="Add"
          title="Add"
        >
          <svg
            v-if="loading"
            class="w-3.5 h-3.5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke-width="4"
            ></circle>
            <path class="opacity-75" stroke-width="4" d="M4 12a8 8 0 018-8" />
          </svg>
          <svg
            v-else
            class="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </template>
      <div v-else :class="chipClasses">
        <template v-if="editingIndex === 0">
          <span class="flex items-center gap-1">
            <svg
              v-if="loading"
              class="w-3.5 h-3.5 animate-spin text-gray-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke-width="4"
              ></circle>
              <path class="opacity-75" stroke-width="4" d="M4 12a8 8 0 018-8" />
            </svg>
            <input
              v-model="inputValue"
              type="text"
              :class="inputClasses"
              @keydown.enter.prevent="handleEnterKey(0)"
              @keydown.esc.prevent="handleEscKey"
              autofocus
            />
            <button
              @mousedown.prevent="commitEdit(0)"
              class="text-green-600 hover:text-green-800"
              aria-label="Confirm"
              title="Confirm"
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
                  d="M5 13l4 4L19 7"
                ></path>
              </svg>
            </button>
            <button
              @mousedown.prevent="cancelEdit"
              class="text-red-600 hover:text-red-800"
              aria-label="Cancel"
              title="Cancel"
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
                ></path>
              </svg>
            </button>
          </span>
        </template>
        <template v-else>
          <span
            class="select-none inline-flex items-center cursor-pointer"
            @click="startEdit(0)"
          >
            {{ singleValueLabel }}
          </span>
          <button
            v-if="canClear"
            class="ml-1 hover:text-red-600 inline-flex items-center disabled:opacity-50"
            @click="clearSingle"
            :disabled="loading"
            aria-label="Clear"
          >
            <svg
              v-if="loading"
              class="w-3.5 h-3.5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke-width="4"
              ></circle>
              <path class="opacity-75" stroke-width="4" d="M4 12a8 8 0 018-8" />
            </svg>
            <span v-else>×</span>
          </button>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: [Array, String, Number, Boolean, null], default: '' },
  emptyLabel: { type: String, default: '-' },
  variant: {
    type: String,
    default: 'gray'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  maxDisplay: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const isArray = computed(() => Array.isArray(props.modelValue))
const chips = computed(() =>
  Array.isArray(props.modelValue) ? props.modelValue : []
)
const singleValueLabel = computed(() => {
  if (chips.value.length === 0 && !isArray.value) {
    return props.modelValue === null ||
      props.modelValue === undefined ||
      props.modelValue === ''
      ? props.emptyLabel
      : String(props.modelValue)
  }
  return String(props.modelValue ?? props.emptyLabel)
})
const canClear = computed(
  () =>
    !isArray.value &&
    props.modelValue !== null &&
    props.modelValue !== undefined &&
    props.modelValue !== ''
)

const editingIndex = ref(-1)
const inputValue = ref('')
const originalValue = ref('')
const showAll = ref(false)

const shouldLimit = computed(
  () =>
    isArray.value &&
    props.maxDisplay > 0 &&
    chips.value.length > props.maxDisplay
)

const visibleIndexes = computed(() => {
  if (!isArray.value) return []
  const total = chips.value.length
  if (!shouldLimit.value || showAll.value) {
    return chips.value.map((_, index) => index)
  }

  const limit = Math.min(props.maxDisplay, total)
  const indexes = Array.from({ length: limit }, (_, index) => index)

  if (
    editingIndex.value >= 0 &&
    editingIndex.value < total &&
    !indexes.includes(editingIndex.value)
  ) {
    indexes[indexes.length - 1] = editingIndex.value
  }

  return indexes
})

const remainingCount = computed(() => {
  if (!shouldLimit.value) return 0
  return chips.value.length - props.maxDisplay
})

watch(
  () => props.modelValue,
  () => {
    // Only reset editingIndex if we're not currently editing
    // This prevents resetting when we add a new chip and start editing it
    if (editingIndex.value === -1) {
      return
    }
    // If we're editing, check if the item we're editing still exists
    if (isArray.value && editingIndex.value >= 0) {
      const currentChips = Array.isArray(props.modelValue)
        ? props.modelValue
        : []
      // If the array length changed or the item at our index is different, reset
      if (editingIndex.value >= currentChips.length) {
        editingIndex.value = -1
      }
      // Otherwise keep editing (the value might have been updated externally)
    } else {
      editingIndex.value = -1
    }
  },
  { immediate: false }
)

watch(
  () => chips.value.length,
  (length) => {
    if (props.maxDisplay > 0 && length <= props.maxDisplay) {
      showAll.value = false
    }
  }
)

const handleEnterKey = (index) => {
  commitEdit(index)
}

const handleEscKey = () => {
  cancelEdit()
}

const startEdit = (index) => {
  if (props.disabled) return
  editingIndex.value = index
  if (isArray.value) {
    inputValue.value = chips.value[index] ?? ''
    originalValue.value = inputValue.value
  } else {
    inputValue.value = String(props.modelValue ?? '')
    originalValue.value = inputValue.value
  }
}

const cancelEdit = () => {
  // If canceling a newly added empty tag, remove it from the array
  if (isArray.value && editingIndex.value >= 0) {
    const originalWasEmpty = originalValue.value === ''
    if (originalWasEmpty) {
      const next = [...chips.value]
      next.splice(editingIndex.value, 1)
      emit('update:modelValue', next)
      emit('change', next)
    }
  }
  editingIndex.value = -1
}

const commitEdit = (index) => {
  if (isArray.value) {
    const trimmedValue = inputValue.value.trim()
    const next = [...chips.value]
    const originalWasEmpty = originalValue.value === ''

    if (trimmedValue === '') {
      // If empty value
      if (originalWasEmpty) {
        // Remove newly added empty tag
        next.splice(index, 1)
      } else {
        // Restore original value when editing existing tag
        next[index] = originalValue.value
      }
    } else {
      // Update with trimmed value
      next[index] = trimmedValue
    }

    emit('update:modelValue', next)
    emit('change', next)
  } else {
    const trimmedValue = inputValue.value.trim()
    emit('update:modelValue', trimmedValue)
    emit('change', trimmedValue)
  }
  editingIndex.value = -1
}

const addChip = async () => {
  if (!isArray.value) return
  if (props.disabled) return

  let next = [...chips.value, '']
  const newIndex = next.length - 1
  // Emit the update first
  emit('update:modelValue', next)
  // Wait for the update to be processed, then set editingIndex
  await nextTick()
  editingIndex.value = newIndex
  inputValue.value = ''
  originalValue.value = ''
}

const removeChip = (index) => {
  if (!isArray.value) return
  if (props.disabled) return
  const next = chips.value.filter((_, i) => i !== index)
  emit('update:modelValue', next)
  emit('change', next)
}

const clearSingle = () => {
  if (isArray.value) return
  if (props.disabled) return
  emit('update:modelValue', '')
  emit('change', '')
}

const isSingleEmpty = computed(() => {
  if (isArray.value) return false
  return (
    props.modelValue === null ||
    props.modelValue === undefined ||
    props.modelValue === ''
  )
})

const chipClasses = computed(() => {
  const base =
    'inline-flex items-center gap-1 px-2 h-6 rounded-md ' +
    'text-xs font-medium select-none'
  const map = {
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    purple: 'bg-purple-100 text-purple-800',
    rose: 'bg-rose-100 text-rose-800',
    amber: 'bg-amber-100 text-amber-800',
    gray: 'bg-gray-100 text-gray-800'
  }
  return `${base} ${map[props.variant] || map.gray}`
})

const inputClasses = computed(() => {
  const base = 'px-1 py-0.5 rounded border focus:ring-0 focus:outline-none '
  const map = {
    blue: 'border-blue-300 focus:border-blue-500',
    green: 'border-green-300 focus:border-green-500',
    purple: 'border-purple-300 focus:border-purple-500',
    rose: 'border-rose-300 focus:border-rose-500',
    amber: 'border-amber-300 focus:border-amber-500',
    gray: 'border-gray-300 focus:border-gray-500'
  }
  return `${base} ${map[props.variant] || map.gray}`
})

const addBtnClasses = computed(() => {
  const base =
    'inline-flex items-center justify-center h-6 w-6 rounded ' +
    'border hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
  const map = {
    blue: 'text-blue-700 border-blue-200',
    green: 'text-green-700 border-green-200',
    purple: 'text-purple-700 border-purple-200',
    rose: 'text-rose-700 border-rose-200',
    amber: 'text-amber-700 border-amber-200',
    gray: 'text-gray-700 border-gray-200'
  }
  return `${base} ${map[props.variant] || map.gray}`
})
</script>

<style scoped></style>
