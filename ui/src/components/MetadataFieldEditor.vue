<template>
  <BaseModal :show="show" :title="modalTitle" @close="onCancel">
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="text-xs text-gray-500">
          {{ t('common.key') }}:
          <span class="font-medium text-gray-700">{{ fieldKey || '-' }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="px-2 py-1 text-xs rounded-md border border-gray-200 hover:bg-gray-50"
            @click="resetToOriginal"
            type="button"
            title="Reset"
          >
            Reset
          </button>
          <button
            class="px-2 py-1 text-xs rounded-md border border-gray-200 hover:bg-gray-50"
            @click="clearValue"
            type="button"
            title="Clear"
          >
            Clear
          </button>
        </div>
      </div>

      <div class="flex items-center gap-2 text-xs">
        <button
          :class="[
            'px-2 py-1 rounded-md border',
            inputMode === 'text'
              ? 'bg-primary-50 border-primary-200 text-primary-700'
              : 'border-gray-200 hover:bg-gray-50'
          ]"
          @click="forceTextMode"
          type="button"
        >
          Text
        </button>
        <button
          :class="[
            'px-2 py-1 rounded-md border',
            inputMode === 'json'
              ? 'bg-primary-50 border-primary-200 text-primary-700'
              : 'border-gray-200 hover:bg-gray-50'
          ]"
          @click="forceJsonMode"
          type="button"
        >
          JSON
        </button>
      </div>
      <div v-if="inputMode === 'text'">
        <label class="block text-sm font-medium text-gray-700 mb-1">{{
          fieldLabel
        }}</label>
        <input
          v-model="localValue"
          type="text"
          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          :placeholder="placeholder"
          autofocus
        />
        <div class="mt-1 text-xs text-gray-400">
          {{ textCount }} {{ t('common.characters') }}
        </div>
      </div>

      <div v-else>
        <label class="block text-sm font-medium text-gray-700 mb-1"
          >{{ fieldLabel }} (JSON)</label
        >
        <textarea
          v-model="localText"
          rows="6"
          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          :placeholder="jsonPlaceholder"
        />
        <div class="mt-2 flex items-center gap-2">
          <button
            class="px-2 py-1 text-xs rounded-md border border-gray-200 hover:bg-gray-50"
            type="button"
            @click="beautifyJson"
          >
            Beautify
          </button>
          <span class="text-xs text-gray-400">{{ jsonBytes }} bytes</span>
        </div>
        <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
      </div>
    </div>

    <template #footer>
      <div class="w-full flex items-center justify-end gap-2">
        <BaseButton variant="secondary" @click="onCancel">{{
          t('common.cancel')
        }}</BaseButton>
        <BaseButton :loading="saving" variant="primary" @click="onSave">{{
          t('common.save')
        }}</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  fieldKey: { type: String, default: '' },
  value: { type: [String, Number, Array, Object, Boolean, null], default: '' },
  type: { type: String, default: 'auto' },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['cancel', 'save'])
const { t } = useI18n()

const saving = ref(false)
const error = ref('')
const localValue = ref('')
const localText = ref('')
const jsonPlaceholder = 'Enter JSON value, e.g. [tag1, tag2]'
const originalValue = ref(undefined)

const modalTitle = computed(() =>
  props.fieldKey ? `${t('common.edit')} ${props.fieldKey}` : t('common.edit')
)
const fieldLabel = computed(() => props.fieldKey || t('common.value'))

const mode = ref('auto')
const inputMode = computed(() => {
  if (props.type === 'text') return 'text'
  if (props.type === 'json') return 'json'
  if (mode.value === 'text') return 'text'
  if (mode.value === 'json') return 'json'
  const v = props.value
  const isTextLike =
    typeof v === 'string' ||
    typeof v === 'number' ||
    v === null ||
    v === undefined ||
    typeof v === 'boolean'
  return isTextLike ? 'text' : 'json'
})

watch(
  () => props.value,
  (v) => {
    error.value = ''
    originalValue.value = v
    if (inputMode.value === 'text') {
      localValue.value = v ?? ''
    } else {
      try {
        localText.value = v !== undefined ? JSON.stringify(v, null, 2) : ''
      } catch (e) {
        localText.value = ''
      }
    }
  },
  { immediate: true }
)

const textCount = computed(() => String(localValue.value ?? '').length)
const jsonBytes = computed(() => new Blob([String(localText.value ?? '')]).size)

const forceTextMode = () => {
  mode.value = 'text'
}
const forceJsonMode = () => {
  mode.value = 'json'
}
const resetToOriginal = () => {
  error.value = ''
  if (inputMode.value === 'text') {
    localValue.value = originalValue.value ?? ''
  } else {
    try {
      localText.value =
        originalValue.value !== undefined
          ? JSON.stringify(originalValue.value, null, 2)
          : ''
    } catch (e) {
      localText.value = ''
    }
  }
}
const clearValue = () => {
  error.value = ''
  if (inputMode.value === 'text') {
    localValue.value = ''
  } else {
    localText.value = ''
  }
}
const beautifyJson = () => {
  try {
    const obj = localText.value ? JSON.parse(localText.value) : null
    localText.value = obj !== null ? JSON.stringify(obj, null, 2) : ''
    error.value = ''
  } catch (e) {
    error.value = t('common.invalidJson')
  }
}

const onCancel = () => {
  emit('cancel')
}

const onSave = async () => {
  error.value = ''
  saving.value = true
  try {
    let out
    if (inputMode.value === 'text') {
      out = localValue.value
    } else {
      try {
        out = localText.value ? JSON.parse(localText.value) : null
      } catch (e) {
        error.value = t('common.invalidJson')
        saving.value = false
        return
      }
    }
    emit('save', out)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped></style>
