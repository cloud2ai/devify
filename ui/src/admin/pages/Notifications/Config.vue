<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('notificationManagement.settings.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('notificationManagement.settings.subtitle') }}
        </p>
      </div>

      <div
        class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
      >
        <div class="p-6">
          <BaseLoading v-if="loading" />
          <template v-else>
            <h2 class="text-base font-semibold text-gray-900 mb-6">
              {{ t('notificationManagement.settings.scheduleSection') }}
            </h2>

            <section
              class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start pb-6"
            >
              <div class="md:col-span-2">
                <h3 class="text-sm font-semibold text-gray-900 mb-1">
                  {{ t('notificationManagement.settings.retentionTitle') }}
                </h3>
                <p class="text-sm text-gray-600">
                  {{ t('notificationManagement.settings.retentionDesc') }}
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
                      t(
                        'notificationManagement.settings.retentionDaysPlaceholder'
                      )
                    "
                    class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <span class="text-sm text-gray-500 w-14">
                    {{ t('notificationManagement.settings.daysUnit') }}
                  </span>
                </div>
              </div>
            </section>

            <section class="pt-6 pb-6 border-t border-gray-200">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
                <div class="md:col-span-2">
                  <h3 class="text-sm font-semibold text-gray-900 mb-1">
                    {{ t('notificationManagement.settings.cleanupTitle') }}
                  </h3>
                  <p class="text-sm text-gray-600">
                    {{ t('notificationManagement.settings.cleanupDesc') }}
                  </p>
                </div>
                <div class="md:col-span-1 flex justify-end">
                  <div class="w-full md:w-64 flex justify-end">
                    <label
                      class="relative inline-flex items-center cursor-pointer"
                    >
                      <input
                        v-model="form.cleanup_enabled"
                        type="checkbox"
                        class="sr-only peer"
                      />
                      <div
                        class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"
                      />
                    </label>
                  </div>
                </div>
              </div>
              <div
                class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center mt-4"
              >
                <div class="md:col-span-2">
                  <label class="text-sm font-medium text-gray-700">
                    {{ t('notificationManagement.settings.cleanupCrontab') }}
                  </label>
                  <p class="text-xs text-gray-500 mt-0.5">
                    {{ t('notificationManagement.settings.crontabHelp') }}
                  </p>
                </div>
                <div class="md:col-span-1 flex justify-end">
                  <div class="w-full md:w-64">
                    <input
                      v-model="form.cleanup_crontab"
                      type="text"
                      :placeholder="
                        t(
                          'notificationManagement.settings.cleanupCrontabPlaceholder'
                        )
                      "
                      :disabled="!form.cleanup_enabled"
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
                {{ t('notificationManagement.settings.reset') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :loading="saving"
                @click="saveConfig"
              >
                {{ t('notificationManagement.settings.saveChanges') }}
              </BaseButton>
            </div>
            <p v-if="saveError" class="text-sm text-red-600 mt-2">
              {{ saveError }}
            </p>
            <p v-if="saveSuccess" class="text-sm text-green-600 mt-2">
              {{ t('notificationManagement.settings.saveSuccess') }}
            </p>
          </template>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { notificationsAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const { showSuccess, showError } = useToast()
const loading = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const form = reactive({
  retention_days: 180,
  cleanup_enabled: true,
  cleanup_crontab: '0 2 * * *'
})

const initialValues = reactive({
  retention_days: 180,
  cleanup_enabled: true,
  cleanup_crontab: '0 2 * * *'
})

function resetForm() {
  form.retention_days = initialValues.retention_days
  form.cleanup_enabled = initialValues.cleanup_enabled
  form.cleanup_crontab = initialValues.cleanup_crontab
  saveError.value = ''
  saveSuccess.value = false
}

function assignFromValue(raw) {
  if (!raw || typeof raw !== 'object') return
  const rd = raw.retention_days
  form.retention_days = typeof rd === 'number' && rd > 0 ? rd : 180
  form.cleanup_enabled = raw.cleanup_enabled !== false
  form.cleanup_crontab =
    typeof raw.cleanup_crontab === 'string' && raw.cleanup_crontab.trim()
      ? raw.cleanup_crontab.trim()
      : '0 2 * * *'
  initialValues.retention_days = form.retention_days
  initialValues.cleanup_enabled = form.cleanup_enabled
  initialValues.cleanup_crontab = form.cleanup_crontab
}

async function load() {
  loading.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const data = await notificationsAdminApi.getGlobalConfig()
    const raw = data?.value
    assignFromValue(raw)
  } catch {
    assignFromValue(null)
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saveError.value = ''
  saveSuccess.value = false
  const value = {
    retention_days: Math.max(
      1,
      Math.min(3650, Number(form.retention_days) || 180)
    ),
    cleanup_enabled: !!form.cleanup_enabled,
    cleanup_crontab: (form.cleanup_crontab || '').trim() || '0 2 * * *'
  }
  saving.value = true
  try {
    await notificationsAdminApi.putGlobalConfig(value)
    initialValues.retention_days = value.retention_days
    initialValues.cleanup_enabled = value.cleanup_enabled
    initialValues.cleanup_crontab = value.cleanup_crontab
    saveSuccess.value = true
    showSuccess(t('notificationManagement.settings.saveSuccess'))
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e) {
    const detail = e?.response?.data?.data?.detail ?? e?.response?.data?.detail
    saveError.value =
      detail || e?.message || t('notificationManagement.settings.saveFailed')
    showError(saveError.value)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
})
</script>
