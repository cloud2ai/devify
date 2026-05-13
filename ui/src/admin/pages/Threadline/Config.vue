<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('threadline.config.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('threadline.config.subtitle') }}
        </p>
        <p class="mt-1 text-xs text-gray-400">
          {{ t('threadline.config.legacyHint') }}
        </p>
      </div>

      <div
        class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
      >
        <div class="p-6">
          <BaseLoading v-if="loadingConfig || loadingModels" />
          <template v-else>
            <h2 class="text-base font-semibold text-gray-900 mb-6">
              {{ t('threadline.config.sectionTitle') }}
            </h2>

            <div class="space-y-4 pb-6">
              <section class="rounded-xl border border-gray-200 bg-gray-50 p-5">
                <div class="space-y-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('threadline.config.imageModelTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('threadline.config.imageModelDesc') }}
                    </p>
                  </div>
                  <div class="max-w-xl">
                    <select
                      v-model="form.image_llm_config_uuid"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      <option value="">
                        {{ t('threadline.config.selectPlaceholder') }}
                      </option>
                      <option
                        v-for="model in modelOptions"
                        :key="`image-${model.uuid}`"
                        :value="model.uuid"
                      >
                        {{ modelLabel(model) }}
                      </option>
                    </select>
                  </div>
                </div>
              </section>

              <section class="rounded-xl border border-gray-200 bg-gray-50 p-5">
                <div class="space-y-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('threadline.config.textModelTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('threadline.config.textModelDesc') }}
                    </p>
                  </div>
                  <div class="max-w-xl">
                    <select
                      v-model="form.text_llm_config_uuid"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      <option value="">
                        {{ t('threadline.config.selectPlaceholder') }}
                      </option>
                      <option
                        v-for="model in modelOptions"
                        :key="`text-${model.uuid}`"
                        :value="model.uuid"
                      >
                        {{ modelLabel(model) }}
                      </option>
                    </select>
                  </div>
                </div>
              </section>

              <section class="rounded-xl border border-gray-200 bg-gray-50 p-5">
                <div class="space-y-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('threadline.config.notificationChannelTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('threadline.config.notificationChannelDesc') }}
                    </p>
                  </div>
                  <div class="max-w-xl">
                    <select
                      v-model="form.notification_channel_uuid"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      :disabled="loadingChannels || channelOptions.length === 0"
                    >
                      <option value="">
                        {{
                          t('threadline.config.notificationChannelPlaceholder')
                        }}
                      </option>
                      <option
                        v-for="channel in channelOptions"
                        :key="channel.uuid"
                        :value="channel.uuid"
                      >
                        {{ channelLabel(channel) }}
                      </option>
                    </select>
                    <p
                      v-if="!loadingChannels && channelOptions.length === 0"
                      class="mt-1 text-xs text-amber-600"
                    >
                      {{ t('threadline.config.noNotificationChannels') }}
                    </p>
                  </div>
                </div>
              </section>
            </div>

            <div
              class="flex items-center justify-end gap-3 border-t border-gray-200 pt-6"
            >
              <BaseButton
                variant="secondary"
                size="sm"
                :disabled="saving"
                @click="resetForm"
              >
                {{ t('threadline.config.reset') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :loading="saving"
                @click="saveConfig"
              >
                {{ t('threadline.config.saveChanges') }}
              </BaseButton>
            </div>

            <p v-if="saveError" class="mt-2 text-sm text-red-600">
              {{ saveError }}
            </p>
            <p v-if="saveSuccess" class="mt-2 text-sm text-green-600">
              {{ t('threadline.config.saveSuccess') }}
            </p>

            <div class="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-5">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('threadline.config.relayConfigTitle') }}
                  </h3>
                  <p class="mt-1 text-sm text-gray-600">
                    {{ t('threadline.config.relayConfigDesc') }}
                  </p>
                </div>
                <BaseButton
                  variant="primary"
                  size="sm"
                  :loading="relaySaving"
                  @click="saveRelayConfig"
                >
                  {{ t('threadline.config.saveRelayChanges') }}
                </BaseButton>
              </div>
              <p v-if="relaySaveError" class="mt-3 text-sm text-red-600">
                {{ relaySaveError }}
              </p>
              <p v-if="relaySaveSuccess" class="mt-3 text-sm text-green-600">
                {{ t('threadline.config.relaySaveSuccess') }}
              </p>
            </div>
          </template>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import {
  llmAdminApi,
  notificationsAdminApi,
  relayAdminApi,
  threadlineAdminApi
} from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loadingConfig = ref(false)
const loadingModels = ref(false)
const loadingChannels = ref(false)
const loadingRelayConfig = ref(false)
const saving = ref(false)
const relaySaving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const relaySaveError = ref('')
const relaySaveSuccess = ref(false)
const modelOptions = ref([])
const channelOptions = ref([])
const relayForm = reactive({
  llm_config_uuid: ''
})
const relayInitialValues = reactive({
  llm_config_uuid: ''
})

const form = reactive({
  image_llm_config_uuid: '',
  text_llm_config_uuid: '',
  notification_channel_uuid: ''
})

const initialValues = reactive({
  image_llm_config_uuid: '',
  text_llm_config_uuid: '',
  notification_channel_uuid: ''
})

function modelLabel(model) {
  const modelName =
    model.config?.model ||
    model.config?.deployment ||
    model.config?.name ||
    model.provider ||
    model.uuid
  const provider = model.provider || 'unknown'
  return `${provider} / ${modelName}`
}

function channelLabel(channel) {
  const name = channel.name || channel.uuid
  const scope =
    channel.scope === 'global'
      ? t('notificationManagement.channels.scopeGlobal')
      : t('notificationManagement.channels.scopeUser')
  return `${name} (${scope})`
}

function resetForm() {
  form.image_llm_config_uuid = initialValues.image_llm_config_uuid
  form.text_llm_config_uuid = initialValues.text_llm_config_uuid
  form.notification_channel_uuid = initialValues.notification_channel_uuid
  saveError.value = ''
  saveSuccess.value = false
}

function applyConfig(raw) {
  if (!raw || typeof raw !== 'object') return
  form.image_llm_config_uuid = raw.image_llm_config_uuid || ''
  form.text_llm_config_uuid = raw.text_llm_config_uuid || ''
  form.notification_channel_uuid = raw.notification_channel_uuid || ''
  initialValues.image_llm_config_uuid = form.image_llm_config_uuid
  initialValues.text_llm_config_uuid = form.text_llm_config_uuid
  initialValues.notification_channel_uuid = form.notification_channel_uuid
}

function applyRelayConfig(raw) {
  if (!raw || typeof raw !== 'object') return
  relayForm.llm_config_uuid = raw.llm_config_uuid || ''
  relayInitialValues.llm_config_uuid = relayForm.llm_config_uuid
}

async function loadModels() {
  loadingModels.value = true
  try {
    const data = await llmAdminApi.getLLMConfig()
    modelOptions.value = Array.isArray(data)
      ? data
          .filter((item) => item && typeof item === 'object')
          .map((item) => ({
            ...item,
            uuid: String(item.uuid || ''),
            config: item.config || {}
          }))
      : []
  } catch (error) {
    modelOptions.value = []
    showError(extractErrorMessage(error, t('common.error')))
  } finally {
    loadingModels.value = false
  }
}

async function loadChannels() {
  loadingChannels.value = true
  try {
    const data = await notificationsAdminApi.getChannels({
      channel_type: 'webhook'
    })
    const rawList = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : Array.isArray(data?.list)
          ? data.list
          : []
    channelOptions.value = rawList
      .filter((item) => item && typeof item === 'object')
      .map((item) => ({
        ...item,
        uuid: String(item.uuid || ''),
        name: item.name || '',
        scope: item.scope || (item.user_id ? 'user' : 'global')
      }))
  } catch (error) {
    channelOptions.value = []
    showError(extractErrorMessage(error, t('common.error')))
  } finally {
    loadingChannels.value = false
  }
}

async function loadConfig() {
  loadingConfig.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const data = await threadlineAdminApi.getWorkflowConfig()
    applyConfig(data)
  } catch (error) {
    saveError.value = extractErrorMessage(error, t('common.error'))
    showError(saveError.value)
  } finally {
    loadingConfig.value = false
  }
}

async function loadRelayConfig() {
  loadingRelayConfig.value = true
  relaySaveError.value = ''
  relaySaveSuccess.value = false
  try {
    const data = await relayAdminApi.getRelayConfig()
    applyRelayConfig(data)
  } catch (error) {
    relaySaveError.value = extractErrorMessage(error, t('common.error'))
    showError(relaySaveError.value)
  } finally {
    loadingRelayConfig.value = false
  }
}

async function loadAll() {
  await Promise.all([
    loadModels(),
    loadChannels(),
    loadConfig(),
    loadRelayConfig()
  ])
}

async function saveConfig() {
  saveError.value = ''
  saveSuccess.value = false

  if (!form.image_llm_config_uuid || !form.text_llm_config_uuid) {
    saveError.value = t('threadline.config.selectionRequired')
    showError(saveError.value)
    return
  }

  saving.value = true
  try {
    const payload = {
      image_llm_config_uuid: form.image_llm_config_uuid || null,
      text_llm_config_uuid: form.text_llm_config_uuid || null,
      notification_channel_uuid: form.notification_channel_uuid || null
    }
    const data = await threadlineAdminApi.updateWorkflowConfig(payload)
    applyConfig(data)
    saveSuccess.value = true
    showSuccess(t('threadline.config.saveSuccess'))
    setTimeout(() => {
      saveSuccess.value = false
    }, 2500)
  } catch (error) {
    saveError.value = extractErrorMessage(
      error,
      t('threadline.config.saveFailed')
    )
    showError(saveError.value)
  } finally {
    saving.value = false
  }
}

async function saveRelayConfig() {
  relaySaveError.value = ''
  relaySaveSuccess.value = false
  relaySaving.value = true
  try {
    const payload = {
      llm_config_uuid: relayForm.llm_config_uuid || null
    }
    const data = await relayAdminApi.updateRelayConfig(payload)
    applyRelayConfig(data)
    relaySaveSuccess.value = true
    showSuccess(t('threadline.config.relaySaveSuccess'))
    setTimeout(() => {
      relaySaveSuccess.value = false
    }, 2500)
  } catch (error) {
    relaySaveError.value = extractErrorMessage(
      error,
      t('threadline.config.relaySaveFailed')
    )
    showError(relaySaveError.value)
  } finally {
    relaySaving.value = false
  }
}

onMounted(() => {
  loadAll()
})
</script>
