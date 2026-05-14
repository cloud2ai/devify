<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-6">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('appSettings.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('appSettings.subtitle') }}
        </p>
      </div>

      <div class="grid gap-6 xl:grid-cols-[1fr_18rem] items-start">
        <div class="space-y-6 min-w-0">
          <section
            id="global-settings"
            class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
          >
            <div class="border-b border-gray-200 px-6 py-5">
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('appSettings.sections.global.title') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('appSettings.sections.global.description') }}
              </p>
            </div>
            <div class="p-6">
              <BaseLoading v-if="loadingThreadlineConfig || loadingChannels" />
              <template v-else>
                <div class="space-y-4">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('appSettings.notificationChannelTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('appSettings.notificationChannelDesc') }}
                    </p>
                  </div>
                  <div class="max-w-xl">
                    <select
                      v-model="threadlineForm.notification_channel_uuid"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      :disabled="loadingChannels || channelOptions.length === 0"
                    >
                      <option value="">
                        {{ t('appSettings.notificationChannelPlaceholder') }}
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
                      {{ t('appSettings.noNotificationChannels') }}
                    </p>
                  </div>
                </div>

                <div
                  class="mt-6 flex items-center justify-end gap-3 border-t border-gray-200 pt-6"
                >
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    :disabled="savingGlobal"
                    @click="resetThreadlineGlobal"
                  >
                    {{ t('appSettings.reset') }}
                  </BaseButton>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    :loading="savingGlobal"
                    @click="saveGlobalSettings"
                  >
                    {{ t('appSettings.saveChanges') }}
                  </BaseButton>
                </div>

                <p v-if="globalSaveError" class="mt-2 text-sm text-red-600">
                  {{ globalSaveError }}
                </p>
                <p v-if="globalSaveSuccess" class="mt-2 text-sm text-green-600">
                  {{ t('appSettings.saveSuccess') }}
                </p>
              </template>
            </div>
          </section>

          <section
            id="threadline-settings"
            class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
          >
            <div class="border-b border-gray-200 px-6 py-5">
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('appSettings.sections.threadline.title') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('appSettings.sections.threadline.description') }}
              </p>
            </div>
            <div class="p-6">
              <BaseLoading v-if="loadingThreadlineConfig || loadingModels" />
              <template v-else>
                <div class="space-y-4 pb-6">
                  <section
                    class="rounded-xl border border-gray-200 bg-gray-50 p-5"
                  >
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
                          v-model="threadlineForm.image_llm_config_uuid"
                          class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        >
                          <option value="">
                            {{ t('appSettings.selectPlaceholder') }}
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

                  <section
                    class="rounded-xl border border-gray-200 bg-gray-50 p-5"
                  >
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
                          v-model="threadlineForm.text_llm_config_uuid"
                          class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        >
                          <option value="">
                            {{ t('appSettings.selectPlaceholder') }}
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
                </div>

                <div
                  class="flex items-center justify-end gap-3 border-t border-gray-200 pt-6"
                >
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    :disabled="savingThreadline"
                    @click="resetThreadlineModels"
                  >
                    {{ t('appSettings.reset') }}
                  </BaseButton>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    :loading="savingThreadline"
                    @click="saveThreadlineSettings"
                  >
                    {{ t('appSettings.saveChanges') }}
                  </BaseButton>
                </div>

                <p v-if="threadlineSaveError" class="mt-2 text-sm text-red-600">
                  {{ threadlineSaveError }}
                </p>
                <p
                  v-if="threadlineSaveSuccess"
                  class="mt-2 text-sm text-green-600"
                >
                  {{ t('appSettings.saveSuccess') }}
                </p>
              </template>
            </div>
          </section>

          <section
            id="relay-settings"
            class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
          >
            <div class="border-b border-gray-200 px-6 py-5">
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('appSettings.sections.relay.title') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('appSettings.sections.relay.description') }}
              </p>
            </div>
            <div class="p-6">
              <BaseLoading v-if="loadingRelayConfig || loadingModels" />
              <template v-else>
                <div class="space-y-3">
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('threadline.config.relayConfigTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ t('threadline.config.relayConfigDesc') }}
                    </p>
                  </div>
                  <div class="max-w-xl">
                    <select
                      v-model="relayForm.llm_config_uuid"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      <option value="">
                        {{ t('appSettings.selectPlaceholder') }}
                      </option>
                      <option
                        v-for="model in modelOptions"
                        :key="`relay-${model.uuid}`"
                        :value="model.uuid"
                      >
                        {{ modelLabel(model) }}
                      </option>
                    </select>
                  </div>
                </div>

                <div
                  class="flex items-center justify-end gap-3 border-t border-gray-200 pt-6"
                >
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    :disabled="savingRelay"
                    @click="resetRelaySettings"
                  >
                    {{ t('appSettings.reset') }}
                  </BaseButton>
                  <BaseButton
                    variant="primary"
                    size="sm"
                    :loading="savingRelay"
                    @click="saveRelaySettings"
                  >
                    {{ t('appSettings.saveChanges') }}
                  </BaseButton>
                </div>

                <p v-if="relaySaveError" class="mt-2 text-sm text-red-600">
                  {{ relaySaveError }}
                </p>
                <p v-if="relaySaveSuccess" class="mt-2 text-sm text-green-600">
                  {{ t('appSettings.saveSuccess') }}
                </p>
              </template>
            </div>
          </section>

        </div>

        <aside class="xl:sticky xl:top-6">
          <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div class="border-b border-gray-200 px-4 py-4">
              <h2 class="text-sm font-semibold text-gray-900">
                {{ t('appSettings.menuTitle') }}
              </h2>
            </div>
            <div class="p-3 space-y-2">
              <button
                v-for="item in sectionItems"
                :key="item.id"
                type="button"
                class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-50"
                @click="gotoSection(item.id)"
              >
                <span>{{ item.label }}</span>
                <svg
                  class="h-4 w-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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

const loadingModels = ref(false)
const loadingChannels = ref(false)
const loadingThreadlineConfig = ref(false)
const loadingRelayConfig = ref(false)

const savingGlobal = ref(false)
const savingThreadline = ref(false)
const savingRelay = ref(false)

const globalSaveError = ref('')
const globalSaveSuccess = ref(false)
const threadlineSaveError = ref('')
const threadlineSaveSuccess = ref(false)
const relaySaveError = ref('')
const relaySaveSuccess = ref(false)

const modelOptions = ref([])
const channelOptions = ref([])

const threadlineForm = reactive({
  image_llm_config_uuid: '',
  text_llm_config_uuid: '',
  notification_channel_uuid: ''
})

const threadlineInitial = reactive({
  image_llm_config_uuid: '',
  text_llm_config_uuid: '',
  notification_channel_uuid: ''
})

const relayForm = reactive({
  llm_config_uuid: ''
})

const relayInitial = reactive({
  llm_config_uuid: ''
})

function normalizeModels(raw) {
  if (!Array.isArray(raw)) return []
  return raw
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      ...item,
      uuid: String(item.uuid || ''),
      config: item.config || {}
    }))
}

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

const sectionItems = computed(() => [
  { id: 'global-settings', label: t('appSettings.sections.global.title') },
  {
    id: 'threadline-settings',
    label: t('appSettings.sections.threadline.title')
  },
  { id: 'relay-settings', label: t('appSettings.sections.relay.title') }
])

function resetThreadlineGlobal() {
  threadlineForm.notification_channel_uuid =
    threadlineInitial.notification_channel_uuid
  globalSaveError.value = ''
  globalSaveSuccess.value = false
}

function resetThreadlineModels() {
  threadlineForm.image_llm_config_uuid = threadlineInitial.image_llm_config_uuid
  threadlineForm.text_llm_config_uuid = threadlineInitial.text_llm_config_uuid
  threadlineSaveError.value = ''
  threadlineSaveSuccess.value = false
}

function resetRelaySettings() {
  relayForm.llm_config_uuid = relayInitial.llm_config_uuid
  relaySaveError.value = ''
  relaySaveSuccess.value = false
}

function applyThreadlineConfig(raw) {
  if (!raw || typeof raw !== 'object') return
  threadlineForm.image_llm_config_uuid = raw.image_llm_config_uuid || ''
  threadlineForm.text_llm_config_uuid = raw.text_llm_config_uuid || ''
  threadlineForm.notification_channel_uuid = raw.notification_channel_uuid || ''
  threadlineInitial.image_llm_config_uuid = threadlineForm.image_llm_config_uuid
  threadlineInitial.text_llm_config_uuid = threadlineForm.text_llm_config_uuid
  threadlineInitial.notification_channel_uuid =
    threadlineForm.notification_channel_uuid
}

function applyRelayConfig(raw) {
  if (!raw || typeof raw !== 'object') return
  relayForm.llm_config_uuid = raw.llm_config_uuid || ''
  relayInitial.llm_config_uuid = relayForm.llm_config_uuid
}

async function loadModels() {
  loadingModels.value = true
  try {
    const data = await llmAdminApi.getLLMConfig()
    modelOptions.value = normalizeModels(data)
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

async function loadThreadlineConfig() {
  loadingThreadlineConfig.value = true
  try {
    const data = await threadlineAdminApi.getWorkflowConfig()
    applyThreadlineConfig(data)
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
  } finally {
    loadingThreadlineConfig.value = false
  }
}

async function loadRelayConfig() {
  loadingRelayConfig.value = true
  try {
    const data = await relayAdminApi.getRelayConfig()
    applyRelayConfig(data)
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
  } finally {
    loadingRelayConfig.value = false
  }
}

async function loadAll() {
  await Promise.all([
    loadModels(),
    loadChannels(),
    loadThreadlineConfig(),
    loadRelayConfig()
  ])
}

async function saveGlobalSettings() {
  globalSaveError.value = ''
  globalSaveSuccess.value = false
  savingGlobal.value = true
  try {
    const data = await threadlineAdminApi.updateWorkflowConfig({
      notification_channel_uuid:
        threadlineForm.notification_channel_uuid || null
    })
    applyThreadlineConfig(data)
    globalSaveSuccess.value = true
    showSuccess(t('appSettings.saveSuccess'))
    setTimeout(() => {
      globalSaveSuccess.value = false
    }, 2500)
  } catch (error) {
    globalSaveError.value = extractErrorMessage(
      error,
      t('appSettings.saveFailed')
    )
    showError(globalSaveError.value)
  } finally {
    savingGlobal.value = false
  }
}

async function saveThreadlineSettings() {
  threadlineSaveError.value = ''
  threadlineSaveSuccess.value = false
  if (
    !threadlineForm.image_llm_config_uuid ||
    !threadlineForm.text_llm_config_uuid
  ) {
    threadlineSaveError.value = t('threadline.config.selectionRequired')
    showError(threadlineSaveError.value)
    return
  }
  savingThreadline.value = true
  try {
    const data = await threadlineAdminApi.updateWorkflowConfig({
      image_llm_config_uuid: threadlineForm.image_llm_config_uuid || null,
      text_llm_config_uuid: threadlineForm.text_llm_config_uuid || null
    })
    applyThreadlineConfig(data)
    threadlineSaveSuccess.value = true
    showSuccess(t('appSettings.saveSuccess'))
    setTimeout(() => {
      threadlineSaveSuccess.value = false
    }, 2500)
  } catch (error) {
    threadlineSaveError.value = extractErrorMessage(
      error,
      t('appSettings.saveFailed')
    )
    showError(threadlineSaveError.value)
  } finally {
    savingThreadline.value = false
  }
}

async function saveRelaySettings() {
  relaySaveError.value = ''
  relaySaveSuccess.value = false
  savingRelay.value = true
  try {
    const data = await relayAdminApi.updateRelayConfig({
      llm_config_uuid: relayForm.llm_config_uuid || null
    })
    applyRelayConfig(data)
    relaySaveSuccess.value = true
    showSuccess(t('appSettings.saveSuccess'))
    setTimeout(() => {
      relaySaveSuccess.value = false
    }, 2500)
  } catch (error) {
    relaySaveError.value = extractErrorMessage(
      error,
      t('appSettings.saveFailed')
    )
    showError(relaySaveError.value)
  } finally {
    savingRelay.value = false
  }
}

function gotoSection(id) {
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  loadAll()
})
</script>
