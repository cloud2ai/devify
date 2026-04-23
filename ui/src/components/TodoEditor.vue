<template>
  <div class="border border-gray-200 rounded-lg p-4 bg-white">
    <div class="space-y-3 text-sm text-gray-700">
      <!-- Validation Error -->
      <div
        v-if="validationError"
        class="rounded-md bg-red-50 border border-red-200 p-2.5"
      >
        <div class="flex gap-2">
          <div class="flex-shrink-0 pt-0.5">
            <svg
              class="h-4 w-4 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="flex-1">
            <p class="text-xs font-medium text-red-800">
              {{ validationError }}
            </p>
          </div>
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          {{ t('todos.content') }} <span class="text-red-500">*</span>
        </label>
        <textarea
          v-model="formData.content"
          rows="3"
          class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
          :class="{ 'border-red-300': validationError }"
          :placeholder="t('todos.content')"
        ></textarea>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            {{ t('todos.priority.label') }}
          </label>
          <select
            v-model="formData.priority"
            class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option :value="null">{{ t('todos.notSet') }}</option>
            <option value="high">{{ t('todos.priority.high') }}</option>
            <option value="medium">{{ t('todos.priority.medium') }}</option>
            <option value="low">{{ t('todos.priority.low') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            {{ t('todos.owner') }}
          </label>
          <input
            v-model="formData.owner"
            type="text"
            class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            :placeholder="t('todos.owner')"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            {{ t('todos.deadline') }}
          </label>
          <BaseDateTimePicker
            v-model="formData.deadline"
            :placeholder="t('todos.deadline')"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            {{ t('todos.location') }}
          </label>
          <input
            v-model="formData.location"
            type="text"
            class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            :placeholder="t('todos.location')"
          />
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 pt-1">
        <BaseButton @click="handleCancel" variant="secondary">
          {{ t('common.cancel') }}
        </BaseButton>
        <BaseButton @click="handleSave" variant="primary" :loading="loading">
          {{ t('common.save') }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDateTimePicker from '@/components/ui/BaseDateTimePicker.vue'

const props = defineProps({
  todo: {
    type: Object,
    default: null
  },
  emailMessageId: {
    type: Number,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['save', 'cancel'])

const { t } = useI18n()

const formData = ref({
  content: '',
  priority: null,
  owner: '',
  deadline: null,
  location: '',
  email_message_id: null
})

const validationError = ref('')

const initializeForm = () => {
  if (props.todo) {
    formData.value = {
      content: props.todo.content || '',
      priority: props.todo.priority || null,
      owner: props.todo.owner || '',
      deadline: props.todo.deadline || null,
      location: props.todo.location || '',
      email_message_id: props.todo.email_message_id || props.emailMessageId
    }
  } else {
    formData.value = {
      content: '',
      priority: null,
      owner: '',
      deadline: null,
      location: '',
      email_message_id: props.emailMessageId
    }
  }
}

watch(
  () => props.todo,
  () => {
    initializeForm()
  },
  { immediate: true }
)

watch(
  () => props.emailMessageId,
  () => {
    if (!props.todo) {
      formData.value.email_message_id = props.emailMessageId
    }
  }
)

const handleSave = () => {
  validationError.value = ''

  if (!formData.value.content.trim()) {
    validationError.value = t('todos.content') + ' ' + t('common.required')
    return
  }

  const data = { ...formData.value }
  if (data.deadline) {
    data.deadline = new Date(data.deadline).toISOString()
  } else {
    data.deadline = null
  }

  if (!data.priority) {
    data.priority = null
  }

  if (!data.owner) {
    data.owner = null
  }

  if (!data.location) {
    data.location = null
  }

  // Ensure email_message_id is set if provided via props
  if (props.emailMessageId && !data.email_message_id) {
    data.email_message_id = props.emailMessageId
  }

  emit('save', data)
}

const handleCancel = () => {
  emit('cancel')
}
</script>
