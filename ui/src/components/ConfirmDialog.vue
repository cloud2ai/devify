<template>
  <BaseModal
    :show="show"
    :title="title"
    @close="handleClose"
    :closeOnBackdrop="false"
  >
    <p class="text-sm text-gray-700">{{ message }}</p>
    <template #footer>
      <div
        class="w-full flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2"
      >
        <BaseButton
          variant="secondary"
          @click="handleClose"
          :disabled="loading"
          class="w-full sm:w-auto"
        >
          {{ t('common.cancel') }}
        </BaseButton>
        <BaseButton
          :variant="variant"
          @click="handleConfirm"
          :loading="loading"
          class="w-full sm:w-auto"
        >
          {{ confirmText || t('common.confirm') }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    required: true
  },
  confirmText: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'danger', 'warning'].includes(value)
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'confirm'])

const { t } = useI18n()

const handleClose = () => {
  emit('close')
}

const handleConfirm = () => {
  emit('confirm')
}
</script>
