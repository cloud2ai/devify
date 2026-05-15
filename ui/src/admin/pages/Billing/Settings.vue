<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('billing.settingsPageTitle') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('billing.settingsPageSubtitle') }}
        </p>
      </div>

      <div class="space-y-6">
        <div class="space-y-6 min-w-0">
          <section
            id="billing-config"
            class="rounded-lg border border-gray-200 bg-white shadow-sm"
          >
            <div class="border-b border-gray-200 px-6 py-5">
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('billing.sections.config') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('billing.sections.configDesc') }}
              </p>
            </div>
            <div class="p-6">
              <BaseLoading v-if="loadingConfig && !configReady" />
              <template v-else>
                <div
                  v-if="statusInfo"
                  class="mb-5 rounded-lg border px-4 py-3 text-sm"
                  :class="
                    statusInfo.stripe_configured
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-amber-200 bg-amber-50 text-amber-800'
                  "
                >
                  <p class="font-medium">
                    {{
                      statusInfo.stripe_configured
                        ? t('billing.status.stripeReady')
                        : t('billing.status.stripeMissing')
                    }}
                  </p>
                  <p class="mt-1">
                    {{
                      statusInfo.stripe_configured
                        ? t('billing.status.stripeReadyHint')
                        : t('billing.status.stripeMissingHint')
                    }}
                  </p>
                </div>

                <form class="space-y-5" @submit.prevent="saveConfig">
                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.stripeLiveMode') }}
                      </span>
                      <select
                        v-model="configForm.stripe_live_mode"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        <option :value="true">
                          {{ t('billing.config.liveMode') }}
                        </option>
                        <option :value="false">
                          {{ t('billing.config.testMode') }}
                        </option>
                      </select>
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.defaultFreeCredits') }}
                      </span>
                      <input
                        v-model.number="configForm.default_free_credits"
                        type="number"
                        min="0"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.workflowCostCredits') }}
                      </span>
                      <input
                        v-model.number="configForm.workflow_cost_credits"
                        type="number"
                        min="1"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.autoRefundSystemErrors') }}
                      </span>
                      <select
                        v-model="configForm.auto_refund_system_errors"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        <option :value="true">
                          {{ t('common.status.success') }}
                        </option>
                        <option :value="false">
                          {{ t('common.status.failed') }}
                        </option>
                      </select>
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.publishableKey') }}
                      </span>
                      <input
                        v-model="configForm.stripe_publishable_key"
                        type="text"
                        autocomplete="off"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="
                          t('billing.config.publishableKeyPlaceholder')
                        "
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.webhookSecret') }}
                      </span>
                      <input
                        v-model="configForm.stripe_webhook_secret"
                        type="password"
                        autocomplete="new-password"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="t('billing.config.secretPlaceholder')"
                      />
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.liveSecretKey') }}
                      </span>
                      <input
                        v-model="configForm.stripe_live_secret_key"
                        type="password"
                        autocomplete="new-password"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="t('billing.config.secretPlaceholder')"
                      />
                    </label>

                    <label class="space-y-1">
                      <span class="block text-sm font-medium text-gray-700">
                        {{ t('billing.config.testSecretKey') }}
                      </span>
                      <input
                        v-model="configForm.stripe_test_secret_key"
                        type="password"
                        autocomplete="new-password"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="t('billing.config.secretPlaceholder')"
                      />
                    </label>
                  </div>

                  <div
                    class="flex items-center justify-end gap-3 border-t border-gray-200 pt-5"
                  >
                    <BaseButton
                      variant="secondary"
                      size="sm"
                      :disabled="savingConfig"
                      @click="resetConfig"
                    >
                      {{ t('common.reset') }}
                    </BaseButton>
                    <BaseButton
                      type="submit"
                      variant="primary"
                      size="sm"
                      :loading="savingConfig"
                    >
                      {{ t('billing.config.saveChanges') }}
                    </BaseButton>
                  </div>
                </form>

                <p v-if="configError" class="mt-3 text-sm text-red-600">
                  {{ configError }}
                </p>
                <p v-if="configSuccess" class="mt-3 text-sm text-green-600">
                  {{ t('billing.config.saveSuccess') }}
                </p>
              </template>
            </div>
          </section>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import { billingAdminApi } from '@/admin/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const toast = useToast()

const loadingConfig = ref(true)
const savingConfig = ref(false)
const configReady = ref(false)
const configError = ref('')
const configSuccess = ref(false)
const statusInfo = ref(null)

const configForm = reactive({
  stripe_live_mode: false,
  stripe_publishable_key: '',
  stripe_live_secret_key: '',
  stripe_test_secret_key: '',
  stripe_webhook_secret: '',
  default_free_credits: 10,
  workflow_cost_credits: 1,
  auto_refund_system_errors: true
})

const initialConfig = reactive({
  stripe_live_mode: false,
  stripe_publishable_key: '',
  stripe_live_secret_key: '',
  stripe_test_secret_key: '',
  stripe_webhook_secret: '',
  default_free_credits: 10,
  workflow_cost_credits: 1,
  auto_refund_system_errors: true
})

function cloneConfig(source) {
  return {
    stripe_live_mode: !!source.stripe_live_mode,
    stripe_publishable_key: source.stripe_publishable_key || '',
    stripe_live_secret_key: source.stripe_live_secret_key || '',
    stripe_test_secret_key: source.stripe_test_secret_key || '',
    stripe_webhook_secret: source.stripe_webhook_secret || '',
    default_free_credits: Number(source.default_free_credits || 0),
    workflow_cost_credits: Number(source.workflow_cost_credits || 1),
    auto_refund_system_errors: source.auto_refund_system_errors !== false
  }
}

function applyConfig(source) {
  const next = cloneConfig(source)
  Object.assign(configForm, next)
  Object.assign(initialConfig, next)
  configReady.value = true
  statusInfo.value = source
}

function resetConfig() {
  Object.assign(configForm, initialConfig)
  configError.value = ''
  configSuccess.value = false
}

async function loadConfig() {
  loadingConfig.value = true
  configError.value = ''
  try {
    const data = await billingAdminApi.getConfig()
    applyConfig(data)
  } catch (error) {
    console.error('Failed to load billing config:', error)
    configError.value = t('billing.config.loadFailed')
  } finally {
    loadingConfig.value = false
  }
}

async function saveConfig() {
  configError.value = ''
  configSuccess.value = false
  savingConfig.value = true
  try {
    const payload = {
      stripe_live_mode: !!configForm.stripe_live_mode,
      stripe_publishable_key: configForm.stripe_publishable_key,
      stripe_live_secret_key: configForm.stripe_live_secret_key,
      stripe_test_secret_key: configForm.stripe_test_secret_key,
      stripe_webhook_secret: configForm.stripe_webhook_secret,
      default_free_credits: Number(configForm.default_free_credits || 0),
      workflow_cost_credits: Number(configForm.workflow_cost_credits || 1),
      auto_refund_system_errors: !!configForm.auto_refund_system_errors
    }
    const data = await billingAdminApi.updateConfig(payload)
    applyConfig(data)
    configSuccess.value = true
    toast.showSuccess(t('billing.config.saveSuccess'))
  } catch (error) {
    console.error('Failed to save billing config:', error)
    configError.value = t('billing.config.saveFailed')
    toast.showError(t('billing.config.saveFailed'))
  } finally {
    savingConfig.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>
