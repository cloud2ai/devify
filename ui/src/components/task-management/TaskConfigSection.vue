<template>
  <div>
    <BaseLoading v-if="loading" />
    <template v-else>
      <h2 class="text-base font-semibold text-gray-900 mb-6">
        {{ t('taskManagement.settings.taskManagementSection') }}
      </h2>

      <section class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start pb-6">
        <div class="md:col-span-2">
          <h3 class="text-sm font-semibold text-gray-900 mb-1">
            {{ t('taskManagement.settings.timeoutTitle') }}
          </h3>
          <p class="text-sm text-gray-600">
            {{ t('taskManagement.settings.timeoutDesc') }}
          </p>
        </div>
        <div class="md:col-span-1 flex justify-end">
          <div class="w-full md:w-64 flex items-center justify-end gap-2">
            <input
              v-model.number="form.timeout_minutes"
              type="number"
              min="1"
              max="1440"
              :placeholder="
                t('taskManagement.settings.timeoutMinutesPlaceholder')
              "
              class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
            />
            <span class="text-sm text-gray-500 w-14">{{
              t('taskManagement.settings.minutesUnit')
            }}</span>
          </div>
        </div>
      </section>

      <section
        class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start pt-6 pb-6 border-t border-gray-200"
      >
        <div class="md:col-span-2">
          <h3 class="text-sm font-semibold text-gray-900 mb-1">
            {{ t('taskManagement.settings.retentionTitle') }}
          </h3>
          <p class="text-sm text-gray-600">
            {{ t('taskManagement.settings.retentionDesc') }}
          </p>
        </div>
        <div class="md:col-span-1 flex justify-end">
          <div class="w-full md:w-64 flex items-center justify-end gap-2">
            <input
              v-model.number="form.retention_days"
              type="number"
              min="1"
              max="3650"
              :placeholder="
                t('taskManagement.settings.retentionDaysPlaceholder')
              "
              class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
            />
            <span class="text-sm text-gray-500 w-14">{{
              t('taskManagement.settings.daysUnit')
            }}</span>
          </div>
        </div>
      </section>

      <section class="pt-6 pb-6 border-t border-gray-200">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <div class="md:col-span-2">
            <h3 class="text-sm font-semibold text-gray-900 mb-1">
              {{ t('taskManagement.settings.cleanupTitle') }}
            </h3>
            <p class="text-sm text-gray-600">
              {{ t('taskManagement.settings.cleanupDesc') }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center mt-4">
          <div class="md:col-span-2">
            <label class="text-sm font-medium text-gray-700">{{
              t('taskManagement.settings.cleanupCrontab')
            }}</label>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ t('taskManagement.settings.crontabHelp') }}
            </p>
          </div>
          <div class="md:col-span-1 flex justify-end">
            <div class="w-full md:w-64">
              <input
                v-model="form.cleanup_crontab"
                type="text"
                :placeholder="
                  t('taskManagement.settings.cleanupCrontabPlaceholder')
                "
                class="rounded-md border border-gray-300 px-3 py-2 text-sm w-full font-mono focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </div>
      </section>

      <section class="pt-6 pb-6 border-t border-gray-200">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <div class="md:col-span-2">
            <h3 class="text-sm font-semibold text-gray-900 mb-1">
              {{ t('taskManagement.settings.markTimeoutTitle') }}
            </h3>
            <p class="text-sm text-gray-600">
              {{ t('taskManagement.settings.markTimeoutDesc') }}
            </p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center mt-4">
          <div class="md:col-span-2">
            <label class="text-sm font-medium text-gray-700">{{
              t('taskManagement.settings.markTimeoutCrontab')
            }}</label>
          </div>
          <div class="md:col-span-1 flex justify-end">
            <div class="w-full md:w-64">
              <input
                v-model="form.mark_timeout_crontab"
                type="text"
                :placeholder="
                  t('taskManagement.settings.markTimeoutCrontabPlaceholder')
                "
                class="rounded-md border border-gray-300 px-3 py-2 text-sm w-full font-mono focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </div>
      </section>

      <div
        class="flex items-center justify-end gap-3 border-t border-gray-200 pt-6"
      >
        <BaseButton
          variant="secondary"
          size="sm"
          :disabled="saving"
          @click="resetForm"
        >
          {{ t('taskManagement.settings.reset') }}
        </BaseButton>
        <BaseButton
          variant="primary"
          size="sm"
          :loading="saving"
          @click="saveConfig"
        >
          {{ t('taskManagement.settings.saveChanges') }}
        </BaseButton>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractResponseData, extractErrorMessage } from '@/utils/api'
import { taskManagementApi } from '@/admin/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loading = ref(false)
const saving = ref(false)
const form = reactive({
  timeout_minutes: 10,
  retention_days: 180,
  cleanup_crontab: '0 2 * * *',
  mark_timeout_crontab: '*/30 * * * *'
})

const initialValues = reactive({
  timeout_minutes: 10,
  retention_days: 180,
  cleanup_crontab: '0 2 * * *',
  mark_timeout_crontab: '*/30 * * * *'
})

function resetForm() {
  form.timeout_minutes = initialValues.timeout_minutes
  form.retention_days = initialValues.retention_days
  form.cleanup_crontab = initialValues.cleanup_crontab
  form.mark_timeout_crontab = initialValues.mark_timeout_crontab
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await taskManagementApi.getConfig()
    const data = extractResponseData(res)
    if (data) {
      if (typeof data.timeout_minutes === 'number') {
        form.timeout_minutes = data.timeout_minutes
        initialValues.timeout_minutes = data.timeout_minutes
      }
      if (typeof data.retention_days === 'number') {
        form.retention_days = data.retention_days
        initialValues.retention_days = data.retention_days
      }
      if (typeof data.cleanup_crontab === 'string') {
        form.cleanup_crontab = data.cleanup_crontab
        initialValues.cleanup_crontab = data.cleanup_crontab
      }
      if (typeof data.mark_timeout_crontab === 'string') {
        form.mark_timeout_crontab = data.mark_timeout_crontab
        initialValues.mark_timeout_crontab = data.mark_timeout_crontab
      }
    }
  } catch (e) {
    showError(extractErrorMessage(e, t('common.error')))
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  const payload = {}
  const tm = Number(form.timeout_minutes)
  const rd = Number(form.retention_days)
  if (tm >= 1 && tm <= 1440) {
    payload.timeout_minutes = tm
  }
  if (rd >= 1 && rd <= 3650) {
    payload.retention_days = rd
  }
  const cc =
    typeof form.cleanup_crontab === 'string' ? form.cleanup_crontab.trim() : ''
  if (cc) {
    payload.cleanup_crontab = cc
  } else {
    showError(t('taskManagement.settings.saveFailed'))
    return
  }
  const mc =
    typeof form.mark_timeout_crontab === 'string'
      ? form.mark_timeout_crontab.trim()
      : ''
  if (mc) {
    payload.mark_timeout_crontab = mc
  } else {
    showError(t('taskManagement.settings.saveFailed'))
    return
  }
  if (Object.keys(payload).length === 0) {
    showError(t('taskManagement.settings.saveFailed'))
    return
  }
  saving.value = true
  try {
    const res = await taskManagementApi.updateConfig(payload)
    const data = extractResponseData(res)
    if (data) {
      if (typeof data.timeout_minutes === 'number') {
        form.timeout_minutes = data.timeout_minutes
        initialValues.timeout_minutes = data.timeout_minutes
      }
      if (typeof data.retention_days === 'number') {
        form.retention_days = data.retention_days
        initialValues.retention_days = data.retention_days
      }
      if (typeof data.cleanup_crontab === 'string') {
        form.cleanup_crontab = data.cleanup_crontab
        initialValues.cleanup_crontab = data.cleanup_crontab
      }
      if (typeof data.mark_timeout_crontab === 'string') {
        form.mark_timeout_crontab = data.mark_timeout_crontab
        initialValues.mark_timeout_crontab = data.mark_timeout_crontab
      }
    }
    showSuccess(t('taskManagement.settings.saveSuccess'))
  } catch (e) {
    showError(extractErrorMessage(e, t('taskManagement.settings.saveFailed')))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>
