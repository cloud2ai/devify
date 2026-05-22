<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-6">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('billing.settingsPageTitle') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('billing.settingsPageSubtitle') }}
        </p>
      </div>

      <BaseLoading v-if="loadingConfig && !configReady" />

      <template v-else>
        <div class="grid gap-6 xl:grid-cols-[1fr_18rem] items-start">
          <div class="space-y-6 min-w-0">
            <section
              id="global-settings"
              class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              <div class="border-b border-gray-200 px-6 py-5">
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.purchaseControl') }}
                </h2>
              </div>
              <div class="p-6">
                <div
                  v-if="configError"
                  class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                >
                  {{ configError }}
                </div>
                <div
                  v-if="configSuccess"
                  class="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700"
                >
                  {{ t('billing.config.saveSuccess') }}
                </div>

                <div class="space-y-4">
                  <label class="block space-y-1">
                    <span class="block text-sm font-medium text-gray-700">
                      {{ t('billing.config.selfPurchaseEnabled') }}
                    </span>
                    <select
                      v-model="configForm.self_purchase_enabled"
                      class="w-full max-w-xl rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      <option :value="true">
                        {{ t('billing.overview.enabled') }}
                      </option>
                      <option :value="false">
                        {{ t('billing.overview.disabled') }}
                      </option>
                    </select>
                  </label>

                  <div class="space-y-3">
                    <p class="text-sm font-medium text-gray-700">
                      {{ t('billing.config.enabledProviders') }}
                    </p>
                    <div class="space-y-3 max-w-xl">
                      <label
                        v-for="provider in providerOptions"
                        :key="provider.value"
                        class="flex items-start gap-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2"
                      >
                        <input
                          v-model="configForm.enabled_providers"
                          type="checkbox"
                          class="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          :value="provider.value"
                        />
                        <div class="min-w-0">
                          <span class="block text-sm font-medium text-gray-900">
                            {{ provider.label }}
                          </span>
                        </div>
                      </label>
                      <div
                        v-if="providerOptions.length === 0"
                        class="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-500"
                      >
                        {{ t('billing.config.noProviders') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section
              id="payment-check-settings"
              class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              <div class="border-b border-gray-200 px-6 py-5">
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.paymentCheck') }}
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                  {{ t('billing.sections.paymentCheckDesc') }}
                </p>
              </div>
              <div class="p-6">
                <div class="rounded-lg border border-gray-200 divide-y divide-gray-200 overflow-hidden">
                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-center">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentCheckEnabled') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.sections.paymentCheckDesc') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1 flex justify-start lg:justify-end">
                      <label class="relative inline-flex cursor-pointer items-center">
                        <input
                          v-model="configForm.payment_check_enabled"
                          type="checkbox"
                          class="peer sr-only"
                        />
                        <div
                          class="peer h-6 w-11 rounded-full bg-gray-200 transition-colors peer-checked:bg-primary-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 after:absolute after:top-[2px] after:left-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-full peer-checked:after:border-white"
                        />
                      </label>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-start">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentCheckSchedule') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentCheckScheduleHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1">
                      <input
                        v-model="configForm.payment_check_schedule"
                        type="text"
                        autocomplete="off"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="t('billing.config.paymentCheckSchedulePlaceholder')"
                      />
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-start">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentCheckProviders') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentCheckProvidersHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1 space-y-3">
                      <label
                        v-for="provider in providerOptions"
                        :key="provider.value"
                        class="flex items-start gap-3 rounded-md border border-gray-200 bg-white px-3 py-2"
                      >
                        <input
                          v-model="configForm.payment_check_providers"
                          type="checkbox"
                          class="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          :value="provider.value"
                        />
                        <div class="min-w-0">
                          <span class="block text-sm font-medium text-gray-900">
                            {{ provider.label }}
                          </span>
                        </div>
                      </label>
                      <div
                        v-if="providerOptions.length === 0"
                        class="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-500"
                      >
                        {{ t('billing.config.noProviders') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section
              id="payment-record-backfill-settings"
              class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              <div class="border-b border-gray-200 px-6 py-5">
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.paymentRecordBackfill') }}
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                  {{ t('billing.sections.paymentRecordBackfillDesc') }}
                </p>
              </div>
              <div class="p-6">
                <div class="rounded-lg border border-gray-200 divide-y divide-gray-200 overflow-hidden">
                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-center">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentRecordBackfillEnabled') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentRecordBackfillLookbackDaysHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1 flex justify-start lg:justify-end">
                      <label class="relative inline-flex cursor-pointer items-center">
                        <input
                          v-model="configForm.payment_record_backfill_enabled"
                          type="checkbox"
                          class="peer sr-only"
                        />
                        <div
                          class="peer h-6 w-11 rounded-full bg-gray-200 transition-colors peer-checked:bg-primary-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 after:absolute after:top-[2px] after:left-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-full peer-checked:after:border-white"
                        />
                      </label>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-start">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentRecordBackfillSchedule') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentRecordBackfillScheduleHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1">
                      <input
                        v-model="configForm.payment_record_backfill_schedule"
                        type="text"
                        autocomplete="off"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                        :placeholder="t('billing.config.paymentRecordBackfillSchedulePlaceholder')"
                      />
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-start">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentRecordBackfillLookbackDays') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentRecordBackfillLookbackDaysHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1">
                      <input
                        v-model.number="configForm.payment_record_backfill_lookback_days"
                        type="number"
                        min="1"
                        class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                  </div>

                  <div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-3 lg:items-start">
                    <div class="lg:col-span-2 min-w-0">
                      <h3 class="text-sm font-semibold text-gray-900">
                        {{ t('billing.config.paymentRecordBackfillProviders') }}
                      </h3>
                      <p class="mt-1 text-sm text-gray-600">
                        {{ t('billing.config.paymentRecordBackfillProvidersHint') }}
                      </p>
                    </div>
                    <div class="lg:col-span-1 space-y-3">
                      <label
                        v-for="provider in providerOptions"
                        :key="provider.value"
                        class="flex items-start gap-3 rounded-md border border-gray-200 bg-white px-3 py-2"
                      >
                        <input
                          v-model="configForm.payment_record_backfill_providers"
                          type="checkbox"
                          class="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          :value="provider.value"
                        />
                        <div class="min-w-0">
                          <span class="block text-sm font-medium text-gray-900">
                            {{ provider.label }}
                          </span>
                        </div>
                      </label>
                      <div
                        v-if="providerOptions.length === 0"
                        class="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-500"
                      >
                        {{ t('billing.config.noProviders') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section
              id="stripe-settings"
              class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              <div class="border-b border-gray-200 px-6 py-5">
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.stripe') }}
                </h2>
              </div>
              <div class="p-6">
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
                      {{ t('billing.config.publishableKey') }}
                    </span>
                    <input
                      v-model="configForm.stripe_publishable_key"
                      type="text"
                      autocomplete="off"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      :placeholder="t('billing.config.publishableKeyPlaceholder')"
                    />
                  </label>

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

                  <label class="space-y-1 md:col-span-2">
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

                  <label class="space-y-1 md:col-span-2">
                    <span class="block text-sm font-medium text-gray-700">
                      {{ t('billing.config.paymentCallbackUrl') }}
                    </span>
                    <input
                      v-model="configForm.payment_callback_url"
                      type="url"
                      autocomplete="off"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      :placeholder="t('billing.config.paymentCallbackUrlPlaceholder')"
                    />
                    <p class="text-xs text-gray-500">
                      {{ t('billing.config.paymentCallbackUrlHint') }}
                    </p>
                  </label>
                </div>
              </div>
            </section>

            <section
              id="credits-policy"
              class="scroll-mt-6 rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden"
            >
              <div class="border-b border-gray-200 px-6 py-5">
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.creditsPolicy') }}
                </h2>
              </div>
              <div class="p-6">
                <div class="grid gap-4 md:grid-cols-2">
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

                  <label class="space-y-1 md:col-span-2">
                    <span class="block text-sm font-medium text-gray-700">
                      {{ t('billing.config.autoRefundSystemErrors') }}
                    </span>
                    <select
                      v-model="configForm.auto_refund_system_errors"
                      class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      <option :value="true">
                        {{ t('billing.overview.enabled') }}
                      </option>
                      <option :value="false">
                        {{ t('billing.overview.disabled') }}
                      </option>
                    </select>
                  </label>
                </div>
              </div>
            </section>

            <div class="flex items-center justify-end gap-3 border-t border-gray-200 pt-5">
              <BaseButton
                variant="secondary"
                size="sm"
                :disabled="savingConfig"
                type="button"
                @click="resetConfig"
              >
                {{ t('common.reset') }}
              </BaseButton>
              <BaseButton
                type="button"
                variant="primary"
                size="sm"
                :loading="savingConfig"
                @click="saveConfig"
              >
                {{ t('billing.config.saveChanges') }}
              </BaseButton>
            </div>
          </div>

          <aside class="xl:sticky xl:top-6">
            <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
              <div class="border-b border-gray-200 px-4 py-4">
                <h2 class="text-sm font-semibold text-gray-900">
                  {{ t('billing.sections.config') }}
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
      </template>
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
const DEFAULT_PAYMENT_CHECK_SCHEDULE = '0 2 * * *'
const DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE = '0 3 * * *'
const DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS = 30

const configForm = reactive({
  stripe_live_mode: false,
  stripe_publishable_key: '',
  stripe_live_secret_key: '',
  stripe_test_secret_key: '',
  stripe_webhook_secret: '',
  payment_callback_url: '',
  self_purchase_enabled: false,
  payment_check_enabled: false,
  payment_check_providers: [],
  payment_check_schedule: DEFAULT_PAYMENT_CHECK_SCHEDULE,
  payment_record_backfill_enabled: false,
  payment_record_backfill_schedule: DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
  payment_record_backfill_lookback_days:
    DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
  payment_record_backfill_providers: [],
  enabled_providers: [],
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
  payment_callback_url: '',
  self_purchase_enabled: false,
  payment_check_enabled: false,
  payment_check_providers: [],
  payment_check_schedule: DEFAULT_PAYMENT_CHECK_SCHEDULE,
  payment_record_backfill_enabled: false,
  payment_record_backfill_schedule: DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
  payment_record_backfill_lookback_days:
    DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
  payment_record_backfill_providers: [],
  enabled_providers: [],
  default_free_credits: 10,
  workflow_cost_credits: 1,
  auto_refund_system_errors: true
})

const sectionItems = [
  { id: 'global-settings', label: t('billing.sections.purchaseControl') },
  { id: 'payment-check-settings', label: t('billing.sections.paymentCheck') },
  {
    id: 'payment-record-backfill-settings',
    label: t('billing.sections.paymentRecordBackfill')
  },
  { id: 'stripe-settings', label: t('billing.sections.stripe') },
  { id: 'credits-policy', label: t('billing.sections.creditsPolicy') },
]

function cloneConfig(source) {
  return {
    stripe_live_mode: !!source.stripe_live_mode,
    stripe_publishable_key: source.stripe_publishable_key || '',
    stripe_live_secret_key: source.stripe_live_secret_key || '',
    stripe_test_secret_key: source.stripe_test_secret_key || '',
    stripe_webhook_secret: source.stripe_webhook_secret || '',
    payment_callback_url: source.payment_callback_url || '',
    self_purchase_enabled: source.self_purchase_enabled === true,
    payment_check_enabled: source.payment_check_enabled === true,
    payment_check_providers: Array.isArray(source.payment_check_providers)
      ? [...source.payment_check_providers]
      : [],
    payment_check_schedule:
      source.payment_check_schedule || DEFAULT_PAYMENT_CHECK_SCHEDULE,
    payment_record_backfill_enabled:
      source.payment_record_backfill_enabled === true,
    payment_record_backfill_schedule:
      source.payment_record_backfill_schedule ||
      DEFAULT_PAYMENT_RECORD_BACKFILL_SCHEDULE,
    payment_record_backfill_lookback_days: Number(
      source.payment_record_backfill_lookback_days ||
        DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS
    ) || DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS,
    payment_record_backfill_providers: Array.isArray(
      source.payment_record_backfill_providers
    )
      ? [...source.payment_record_backfill_providers]
      : [],
    enabled_providers: Array.isArray(source.enabled_providers)
      ? [...source.enabled_providers]
      : [],
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
}

function resetConfig() {
  Object.assign(configForm, initialConfig)
  configError.value = ''
  configSuccess.value = false
}

const providerOptions = [
  {
    value: 'stripe',
    label: 'Stripe',
  },
]

function gotoSection(id) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
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
      payment_callback_url: configForm.payment_callback_url,
      self_purchase_enabled: !!configForm.self_purchase_enabled,
      payment_check_enabled: !!configForm.payment_check_enabled,
      payment_check_providers: [...configForm.payment_check_providers],
      payment_check_schedule: configForm.payment_check_schedule,
      payment_record_backfill_enabled:
        !!configForm.payment_record_backfill_enabled,
      payment_record_backfill_schedule:
        configForm.payment_record_backfill_schedule,
      payment_record_backfill_lookback_days: Number(
        configForm.payment_record_backfill_lookback_days ||
          DEFAULT_PAYMENT_RECORD_BACKFILL_LOOKBACK_DAYS
      ),
      payment_record_backfill_providers: [
        ...configForm.payment_record_backfill_providers
      ],
      enabled_providers: [...configForm.enabled_providers],
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
