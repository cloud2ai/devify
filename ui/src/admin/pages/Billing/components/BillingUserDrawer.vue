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
                      selectedDetailTab === 'payments'
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    "
                    type="button"
                    role="tab"
                    :aria-selected="selectedDetailTab === 'payments'"
                    @click="$emit('update:selectedDetailTab', 'payments')"
                  >
                    {{ t('billing.drawer.tabs.payments') }}
                  </button>
                  <button
                    class="flex-shrink-0 border-b-2 px-1 py-3 text-xs font-medium transition-colors sm:text-sm"
                    :class="
                      selectedDetailTab === 'subscriptions'
                        ? 'border-primary-600 text-primary-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    "
                    type="button"
                    role="tab"
                    :aria-selected="selectedDetailTab === 'subscriptions'"
                    @click="$emit('update:selectedDetailTab', 'subscriptions')"
                  >
                    {{ t('billing.drawer.tabs.subscriptions') }}
                  </button>
                </div>
              </div>
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
              v-else-if="selectedDetailTab === 'payments'"
              class="space-y-3"
            >
              <BaseLoading v-if="detailLoading" />
              <div
                v-else-if="detailPayments.length === 0"
                class="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600"
              >
                {{ t('billing.drawer.noPayments') }}
              </div>
              <div
                v-for="item in detailPayments"
                :key="item.id"
                class="rounded-lg border border-gray-200 p-3 text-sm"
              >
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium text-gray-900">
                    {{ item.status }}
                  </span>
                  <span class="text-gray-500">
                    {{ formatDate(item.created_at) }}
                  </span>
                </div>
                <p class="mt-1 text-gray-600">
                  {{ formatCurrency(item.amount_cents, item.currency) }}
                </p>
                <p class="mt-1 text-gray-500">{{ item.provider_name }}</p>
              </div>
            </section>

            <section v-else class="space-y-3">
              <BaseLoading v-if="detailLoading" />
              <div
                v-else-if="detailSubscriptions.length === 0"
                class="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600"
              >
                {{ t('billing.drawer.noSubscriptions') }}
              </div>
              <div
                v-for="item in detailSubscriptions"
                :key="item.id"
                class="rounded-lg border border-gray-200 p-3 text-sm"
              >
                <div class="flex items-center justify-between gap-3">
                  <span class="font-medium text-gray-900">
                    {{ item.plan_name || '—' }}
                  </span>
                  <span class="text-gray-500">
                    {{ formatDate(item.current_period_end) }}
                  </span>
                </div>
                <p class="mt-1 text-gray-600">{{ item.status }}</p>
                <p class="mt-1 text-gray-500">{{ item.provider_name }}</p>
              </div>
            </section>
          </div>
        </template>
      </div>
    </aside>
  </transition>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t, locale } = useI18n()

defineProps({
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
    default: 'transactions'
  },
  selectedUser: {
    type: Object,
    default: null
  }
})

defineEmits(['close', 'update:selectedDetailTab'])

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
</script>
