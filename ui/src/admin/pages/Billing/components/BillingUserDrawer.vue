<template>
  <transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-0 z-50 bg-gray-900/50"
      aria-hidden="true"
      @click="$emit('close')"
    />
  </transition>

  <transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition-transform duration-250 ease-in"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="open"
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-5xl flex-col bg-white shadow-xl"
      role="region"
      :aria-label="t('billing.drawer.title')"
    >
      <div
        class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4"
      >
        <div>
          <h2 class="text-lg font-semibold text-gray-900">
            {{ selectedUser?.username || t('billing.drawer.title') }}
          </h2>
          <p class="break-all font-mono text-xs text-gray-500">
            {{ selectedUser?.email || '—' }}
          </p>
        </div>
        <button
          type="button"
          class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          :aria-label="t('common.close')"
          @click="$emit('close')"
        >
          <svg
            class="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <BaseLoading v-if="detailLoading" />

        <template v-else-if="selectedUser">
          <div class="space-y-4">
            <section class="space-y-4">
              <div class="border-b border-gray-200">
                <div
                  class="flex gap-6 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
                  role="tablist"
                  :aria-label="t('billing.drawer.title')"
                >
                  <button
                    class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
                    :class="
                      selectedDetailTab === 'overview'
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    "
                    type="button"
                    role="tab"
                    :aria-selected="selectedDetailTab === 'overview'"
                    @click="$emit('update:selectedDetailTab', 'overview')"
                  >
                    {{ t('billing.drawer.tabs.overview') }}
                  </button>
                  <button
                    class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
                    :class="
                      selectedDetailTab === 'transactions'
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    "
                    type="button"
                    role="tab"
                    :aria-selected="selectedDetailTab === 'transactions'"
                    @click="$emit('update:selectedDetailTab', 'transactions')"
                  >
                    {{ t('billing.drawer.tabs.transactions') }}
                  </button>
                  <button
                    class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
                    :class="
                      selectedDetailTab === 'records'
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    "
                    type="button"
                    role="tab"
                    :aria-selected="selectedDetailTab === 'records'"
                    @click="$emit('update:selectedDetailTab', 'records')"
                  >
                    {{ t('billing.drawer.recordsTitle') }}
                  </button>
                </div>
              </div>
            </section>

            <section v-if="selectedDetailTab === 'overview'" class="space-y-4">
              <section class="rounded-lg border border-gray-200 bg-white p-4">
                <div class="mb-3">
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('billing.drawer.currentPlan') }}
                  </h3>
                </div>
                <div class="grid gap-3 md:grid-cols-4">
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.drawer.currentPlan') }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-gray-900">
                      {{
                        selectedUser.plan_name ||
                        t('billing.users.noSubscription')
                      }}
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.drawer.subscriptionStatus') }}
                    </p>
                    <p class="mt-1">
                      <span
                        class="inline-flex rounded-full px-2 py-1 text-xs font-medium"
                        :class="
                          getStatusClass(selectedUser.subscription_status)
                        "
                      >
                        {{
                          formatSubscriptionStatus(
                            selectedUser.subscription_status
                          )
                        }}
                      </span>
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.drawer.subscriptionSource') }}
                    </p>
                    <p class="mt-1 text-sm font-semibold text-gray-900">
                      {{
                        formatSubscriptionSource(
                          selectedUser.provider_key,
                          selectedUser.provider_name
                        )
                      }}
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.drawer.periodEnd') }}
                    </p>
                    <p class="mt-1 text-sm font-semibold text-gray-900">
                      {{ formatDate(selectedUser.period_end) }}
                    </p>
                  </div>
                </div>
              </section>

              <section class="rounded-lg border border-gray-200 bg-white p-4">
                <div class="mb-3">
                  <h3 class="text-sm font-semibold text-gray-900">
                    {{ t('billing.drawer.creditsTitle') }}
                  </h3>
                </div>
                <div class="grid gap-3 md:grid-cols-4">
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.users.availableCredits') }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-gray-900">
                      {{ selectedUser.available_credits }}
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.users.baseCredits') }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-gray-900">
                      {{ selectedUser.base_credits }}
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.users.bonusCredits') }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-gray-900">
                      {{ selectedUser.bonus_credits }}
                    </p>
                  </div>
                  <div class="rounded-lg bg-gray-50 p-3">
                    <p class="text-xs text-gray-500">
                      {{ t('billing.users.consumedCredits') }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-gray-900">
                      {{ selectedUser.consumed_credits }}
                    </p>
                  </div>
                </div>
              </section>
            </section>
            <section
              v-if="selectedDetailTab === 'transactions'"
              class="space-y-3"
            >
              <BaseLoading v-if="detailLoading" />
              <div
                v-else-if="detailTransactions.length === 0"
                class="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600"
              >
                {{ t('billing.drawer.noTransactions') }}
              </div>
              <div
                v-for="item in detailTransactions"
                :key="item.id"
                class="rounded-lg border border-gray-200 p-3 text-sm"
              >
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium text-gray-900">
                    {{ item.transaction_type }}
                  </span>
                  <span class="text-gray-500">
                    {{ formatDate(item.created_at) }}
                  </span>
                </div>
                <p class="mt-1 text-gray-600">{{ item.reason }}</p>
                <p class="mt-1 text-gray-500">
                  {{ t('billing.drawer.amountLabel') }}: {{ item.amount }}
                </p>
              </div>
            </section>

            <section
              v-else-if="selectedDetailTab === 'records'"
              class="space-y-4"
            >
              <section
                class="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
              >
                <div
                  class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
                >
                  <div>
                    <h3 class="text-sm font-semibold text-gray-900">
                      {{ t('billing.drawer.recordsTitle') }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-500">
                      {{ t('billing.drawer.recordsHint') }}
                    </p>
                  </div>
                  <p class="text-xs text-gray-400">
                    {{ t('billing.drawer.recordsFooter') }}
                  </p>
                </div>

                <div class="mt-4 flex flex-wrap gap-2">
                  <span
                    class="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
                  >
                    {{ t('billing.drawer.recordsPayments') }} ·
                    {{ detailPayments.length }}
                  </span>
                  <span
                    class="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
                  >
                    {{ t('billing.drawer.recordsSubscriptions') }} ·
                    {{ detailSubscriptions.length }}
                  </span>
                  <span
                    class="rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
                  >
                    {{ mergedBillingRecords.length }} 条
                  </span>
                </div>
              </section>

              <BaseLoading v-if="detailLoading" />

              <div
                v-else-if="mergedBillingRecords.length === 0"
                class="rounded-2xl border border-dashed border-gray-200 bg-gray-50/80 p-6 text-sm text-gray-500"
              >
                {{ t('billing.drawer.noRecords') }}
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="item in mergedBillingRecords"
                  :key="item.key"
                  class="group rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md"
                >
                  <div class="flex items-start gap-4">
                    <div
                      class="mt-1 h-12 w-1.5 rounded-full"
                      :class="item.accentClass"
                    />

                    <div class="min-w-0 flex-1">
                      <div
                        class="flex flex-wrap items-start justify-between gap-3"
                      >
                        <div class="min-w-0">
                          <div class="flex flex-wrap items-center gap-2">
                            <span
                              class="inline-flex rounded-full px-2 py-1 text-[11px] font-medium"
                              :class="item.kindClass"
                            >
                              {{ item.kindLabel }}
                            </span>
                            <h4
                              class="truncate text-sm font-semibold text-gray-900"
                            >
                              {{ item.title }}
                            </h4>
                          </div>
                          <p class="mt-1 text-xs text-gray-500">
                            {{ item.subtitle }}
                          </p>
                        </div>

                        <div class="text-right">
                          <p
                            class="text-[11px] uppercase tracking-wide text-gray-400"
                          >
                            {{ formatDate(item.timestamp) }}
                          </p>
                          <span
                            class="mt-1 inline-flex rounded-full px-2 py-1 text-[11px] font-medium"
                            :class="item.statusClass"
                          >
                            {{ item.statusLabel }}
                          </span>
                        </div>
                      </div>

                      <div
                        class="mt-4 flex flex-wrap items-center gap-2 text-xs text-gray-500"
                      >
                        <span
                          v-for="meta in item.meta"
                          :key="`${item.key}-${meta.label}`"
                          class="rounded-full bg-gray-50 px-2 py-1"
                        >
                          <span class="font-medium text-gray-600"
                            >{{ meta.label }}:</span
                          >
                          <span class="ml-1 text-gray-500">{{
                            meta.value
                          }}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </template>
      </div>
    </aside>
  </transition>
</template>

<script setup>
import { computed, toRefs } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { formatProviderLabel } from '../utils/provider'

const { t, locale } = useI18n()

const props = defineProps({
  detailLoading: {
    type: Boolean,
    default: false
  },
  detailTransactions: {
    type: Array,
    default: () => []
  },
  detailPayments: {
    type: Array,
    default: () => []
  },
  detailSubscriptions: {
    type: Array,
    default: () => []
  },
  open: {
    type: Boolean,
    default: false
  },
  selectedDetailTab: {
    type: String,
    default: 'overview'
  },
  selectedUser: {
    type: Object,
    default: null
  }
})

const {
  detailLoading,
  detailTransactions,
  detailPayments,
  detailSubscriptions,
  open,
  selectedDetailTab,
  selectedUser
} = toRefs(props)

defineEmits(['close', 'update:selectedDetailTab'])

const mergedBillingRecords = computed(() => {
  const paymentRecords = (detailPayments.value || []).map((item) => ({
    key: `payment-${item.id}`,
    kind: 'payment',
    kindLabel: t('billing.drawer.recordsPayments'),
    kindClass: 'bg-primary-50 text-primary-700',
    timestamp: item.created_at,
    title: formatCurrency(item.amount_cents, item.currency),
    subtitle: item.subscription_plan_name
      ? `${formatSubscriptionSource(item.provider_key, item.provider_name)} · ${item.subscription_plan_name}`
      : formatSubscriptionSource(item.provider_key, item.provider_name),
    status: item.status,
    statusLabel: formatPaymentStatus(item.status),
    statusClass: getPaymentStatusClass(item.status),
    accentClass: getPaymentAccentClass(item.status),
    meta: buildPaymentMeta(item)
  }))

  const subscriptionRecords = (detailSubscriptions.value || []).map((item) => ({
    key: `subscription-${item.id}`,
    kind: 'subscription',
    kindLabel: t('billing.drawer.recordsSubscriptions'),
    kindClass: 'bg-emerald-50 text-emerald-700',
    timestamp: item.created_at,
    title: item.plan_name || t('billing.users.noSubscription'),
    subtitle: formatSubscriptionSource(item.provider_key, item.provider_name),
    status: item.status,
    statusLabel: formatSubscriptionStatus(item.status),
    statusClass: getStatusClass(item.status),
    accentClass: getSubscriptionAccentClass(item.status),
    meta: [
      {
        label: t('billing.drawer.periodEnd'),
        value: formatDate(item.current_period_end)
      },
      {
        label: t('billing.drawer.autoRenew'),
        value: item.auto_renew
          ? t('billing.drawer.autoRenewOn')
          : t('billing.drawer.autoRenewOff')
      }
    ]
  }))

  return [...paymentRecords, ...subscriptionRecords].sort((left, right) => {
    const leftTime = new Date(left.timestamp || 0).getTime()
    const rightTime = new Date(right.timestamp || 0).getTime()
    return rightTime - leftTime
  })
})

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date)
}

function formatCurrency(cents, currency = 'USD') {
  const value = (Number(cents) || 0) / 100
  return new Intl.NumberFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
    style: 'currency',
    currency: (currency || 'USD').toUpperCase()
  }).format(value)
}

function formatPaymentStatus(status) {
  const normalized = (status || '').toLowerCase()
  if (!normalized) {
    return t('common.status.unknown')
  }

  const statusKey = {
    pending: 'common.status.pending',
    succeeded: 'common.status.success',
    failed: 'common.status.failed',
    refunded: 'common.status.refunded'
  }[normalized]

  return statusKey ? t(statusKey) : normalized
}

function buildPaymentMeta(item) {
  const metadata = item?.metadata || {}
  const meta = []
  const invoiceNumber = normalizeText(metadata.invoice_number)
  const billingReason = normalizeText(metadata.billing_reason)
  const paymentIntentId = normalizeText(metadata.payment_intent_id)
  const chargeId = normalizeText(metadata.charge_id)
  const receiptNumber = normalizeText(metadata.receipt_number)
  const customerEmail = normalizeText(metadata.customer_email)
  const source = normalizeText(metadata.source)
  const eventType = normalizeText(metadata.event_type)
  const paymentMethodBrand = normalizeText(metadata.payment_method_brand)
  const paymentMethodLast4 = normalizeText(metadata.payment_method_last4)
  const paymentMethodType = normalizeText(metadata.payment_method_type)

  if (paymentMethodBrand || paymentMethodLast4 || paymentMethodType) {
    meta.push({
      label: t('billing.drawer.paymentMethod'),
      value: [
        paymentMethodBrand,
        paymentMethodLast4 ? `•••• ${paymentMethodLast4}` : '',
        paymentMethodType
      ]
        .filter(Boolean)
        .join(' · ')
    })
  }

  if (invoiceNumber) {
    meta.push({
      label: t('billing.drawer.invoiceNumber'),
      value: shortReference(invoiceNumber)
    })
  }

  if (billingReason) {
    meta.push({
      label: t('billing.drawer.billingReason'),
      value: billingReason
    })
  }

  if (paymentIntentId) {
    meta.push({
      label: t('billing.drawer.paymentIntent'),
      value: shortReference(paymentIntentId)
    })
  }

  if (chargeId) {
    meta.push({
      label: t('billing.drawer.chargeId'),
      value: shortReference(chargeId)
    })
  }

  if (receiptNumber) {
    meta.push({
      label: t('billing.drawer.receiptNumber'),
      value: shortReference(receiptNumber)
    })
  }

  if (customerEmail) {
    meta.push({
      label: t('billing.drawer.customerEmail'),
      value: customerEmail
    })
  }

  if (source) {
    meta.push({
      label: t('billing.drawer.source'),
      value: source
    })
  }

  if (eventType) {
    meta.push({
      label: t('billing.drawer.eventType'),
      value: eventType
    })
  }

  meta.push({
    label: t('billing.drawer.currency'),
    value: (item.currency || 'USD').toUpperCase()
  })

  return meta
}

function normalizeText(value) {
  return String(value || '').trim()
}

function shortReference(value) {
  const text = normalizeText(value)
  if (!text) return '—'
  if (text.length <= 18) return text
  return `${text.slice(0, 8)}…${text.slice(-6)}`
}

function getPaymentStatusClass(status) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'succeeded') {
    return 'bg-emerald-100 text-emerald-800'
  }
  if (normalized === 'failed') {
    return 'bg-rose-100 text-rose-800'
  }
  if (normalized === 'refunded') {
    return 'bg-slate-100 text-slate-700'
  }
  if (normalized === 'pending') {
    return 'bg-amber-100 text-amber-800'
  }
  return 'bg-gray-100 text-gray-600'
}

function formatSubscriptionStatus(status) {
  const normalized = (status || '').toLowerCase()
  if (!normalized) {
    return t('billing.users.noSubscription')
  }

  const statusKey = {
    active: 'billing.status.active',
    canceled: 'billing.status.canceled',
    trialing: 'billing.status.trialing',
    past_due: 'billing.status.pastDue'
  }[normalized]

  return statusKey ? t(statusKey) : normalized
}

function getStatusClass(status) {
  const normalized = (status || '').toLowerCase()
  if (!normalized) {
    return 'bg-amber-100 text-amber-800'
  }
  if (normalized === 'active' || normalized === 'trialing') {
    return 'bg-emerald-100 text-emerald-800'
  }
  if (normalized === 'past_due') {
    return 'bg-rose-100 text-rose-800'
  }
  return 'bg-gray-100 text-gray-600'
}

function getSubscriptionAccentClass(status) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'active' || normalized === 'trialing') {
    return 'bg-emerald-500'
  }
  if (normalized === 'past_due') {
    return 'bg-rose-500'
  }
  if (normalized === 'canceled') {
    return 'bg-gray-400'
  }
  return 'bg-slate-400'
}

function getPaymentAccentClass(status) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'succeeded') {
    return 'bg-primary-500'
  }
  if (normalized === 'failed') {
    return 'bg-rose-500'
  }
  if (normalized === 'refunded') {
    return 'bg-slate-500'
  }
  if (normalized === 'pending') {
    return 'bg-amber-500'
  }
  return 'bg-gray-400'
}

function formatSubscriptionSource(providerKey, providerName) {
  return formatProviderLabel(providerKey, providerName, t)
}
</script>
