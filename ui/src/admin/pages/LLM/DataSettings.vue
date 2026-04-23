<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('llm.dataSettings.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('llm.dataSettings.subtitle') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <BaseLoading v-if="loading" />
          <template v-else>
            <h2 class="text-base font-semibold text-gray-900 mb-6">
              {{ t('llm.dataSettings.sectionTitle') }}
            </h2>

            <section
              class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start pb-6"
            >
              <div class="md:col-span-2">
                <h3 class="text-sm font-semibold text-gray-900 mb-1">
                  {{ t('llm.dataSettings.retentionTitle') }}
                </h3>
                <p class="text-sm text-gray-600">
                  {{ t('llm.dataSettings.retentionDesc') }}
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
                      t('llm.dataSettings.retentionDaysPlaceholder')
                    "
                    class="rounded-md border border-gray-300 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <span class="text-sm text-gray-500 w-14">{{
                    t('llm.dataSettings.daysUnit')
                  }}</span>
                </div>
              </div>
            </section>

            <section class="pt-6 pb-6 border-t border-gray-200">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
                <div class="md:col-span-2">
                  <h3 class="text-sm font-semibold text-gray-900 mb-1">
                    {{ t('llm.dataSettings.cleanupTitle') }}
                  </h3>
                  <p class="text-sm text-gray-600">
                    {{ t('llm.dataSettings.cleanupDesc') }}
                  </p>
                </div>
                <div class="md:col-span-1 flex justify-end">
                  <div class="w-full md:w-64 flex justify-end">
                    <label
                      class="relative inline-flex items-center cursor-pointer"
                    >
                      <input
                        v-model="cleanupEnabled"
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
                  <label class="text-sm font-medium text-gray-700">{{
                    t('llm.dataSettings.cleanupCrontab')
                  }}</label>
                  <p class="text-xs text-gray-500 mt-0.5">
                    {{ t('llm.dataSettings.crontabHelp') }}
                  </p>
                </div>
                <div class="md:col-span-1 flex justify-end">
                  <div class="w-full md:w-64">
                    <input
                      v-model="form.cleanup_crontab"
                      type="text"
                      :placeholder="
                        t('llm.dataSettings.cleanupCrontabPlaceholder')
                      "
                      :disabled="!cleanupEnabled"
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
                    {{ t('llm.dataSettings.aggregationCrontab') }}
                  </h3>
                  <p class="text-sm text-gray-600">
                    {{ t('llm.dataSettings.aggregationCrontabDesc') }}
                  </p>
                  <p class="text-xs text-gray-500 mt-0.5">
                    {{ t('llm.dataSettings.crontabHelp') }}
                  </p>
                </div>
                <div class="md:col-span-1 flex justify-end">
                  <div class="w-full md:w-64">
                    <input
                      v-model="form.aggregation_crontab"
                      type="text"
                      :placeholder="
                        t('llm.dataSettings.aggregationCrontabPlaceholder')
                      "
                      class="rounded-md border border-gray-300 px-3 py-2 text-sm w-full font-mono focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
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
                {{ t('llm.dataSettings.reset') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :loading="saving"
                @click="saveConfig"
              >
                {{ t('llm.dataSettings.saveChanges') }}
              </BaseButton>
            </div>
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
import { extractErrorMessage } from '@/utils/api'
import { llmAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loading = ref(false)
const saving = ref(false)
const cleanupEnabled = ref(true)

const form = reactive({
  retention_days: 365,
  cleanup_crontab: '0 2 * * *',
  aggregation_crontab: '5 * * * *'
})

const initialValues = reactive({
  retention_days: 365,
  cleanup_crontab: '0 2 * * *',
  aggregation_crontab: '5 * * * *'
})

function resetForm() {
  form.retention_days = initialValues.retention_days
  form.cleanup_crontab = initialValues.cleanup_crontab
  form.aggregation_crontab = initialValues.aggregation_crontab
}

async function loadConfig() {
  loading.value = true
  try {
    const raw = await llmAdminApi.getMeteringConfig()
    if (raw && typeof raw === 'object') {
      if (typeof raw.retention_days === 'number') {
        form.retention_days = raw.retention_days
        initialValues.retention_days = raw.retention_days
      }
      if (typeof raw.cleanup_crontab === 'string') {
        form.cleanup_crontab = raw.cleanup_crontab
        initialValues.cleanup_crontab = raw.cleanup_crontab
      }
      if (typeof raw.cleanup_enabled === 'boolean') {
        cleanupEnabled.value = raw.cleanup_enabled
      }
      if (typeof raw.aggregation_crontab === 'string') {
        form.aggregation_crontab = raw.aggregation_crontab
        initialValues.aggregation_crontab = raw.aggregation_crontab
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
  const rd = Number(form.retention_days)
  if (rd >= 1 && rd <= 3650) payload.retention_days = rd
  payload.cleanup_enabled = cleanupEnabled.value
  if (typeof form.cleanup_crontab === 'string' && form.cleanup_crontab.trim()) {
    payload.cleanup_crontab = form.cleanup_crontab.trim()
  }
  if (
    typeof form.aggregation_crontab === 'string' &&
    form.aggregation_crontab.trim()
  ) {
    payload.aggregation_crontab = form.aggregation_crontab.trim()
  }
  if (Object.keys(payload).length === 0) {
    showError(t('llm.dataSettings.saveFailed'))
    return
  }
  saving.value = true
  try {
    const raw = await llmAdminApi.updateMeteringConfig(payload)
    if (raw && typeof raw === 'object') {
      if (typeof raw.retention_days === 'number') {
        form.retention_days = raw.retention_days
        initialValues.retention_days = raw.retention_days
      }
      if (typeof raw.cleanup_crontab === 'string') {
        form.cleanup_crontab = raw.cleanup_crontab
        initialValues.cleanup_crontab = raw.cleanup_crontab
      }
      if (typeof raw.cleanup_enabled === 'boolean')
        cleanupEnabled.value = raw.cleanup_enabled
      if (typeof raw.aggregation_crontab === 'string') {
        form.aggregation_crontab = raw.aggregation_crontab
        initialValues.aggregation_crontab = raw.aggregation_crontab
      }
    }
    showSuccess(t('llm.dataSettings.saveSuccess'))
  } catch (e) {
    showError(extractErrorMessage(e, t('llm.dataSettings.saveFailed')))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>
