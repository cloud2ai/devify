<template>
  <section class="rounded-lg border border-gray-200 bg-white shadow-sm">
    <div class="flex flex-col gap-4 border-b border-gray-200 px-6 py-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <BaseButton
            variant="primary"
            size="sm"
            :disabled="paymentCheckDisabled"
            @click="$emit('payment-check')"
          >
            {{ t('billing.paymentCheck.title') }}
          </BaseButton>
          <BaseButton
            variant="primary"
            size="sm"
            :disabled="paymentRecordBackfillDisabled"
            @click="$emit('payment-record-backfill')"
          >
            {{ t('billing.sections.paymentRecordBackfill') }}
          </BaseButton>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="identityConflictCount > 0"
            type="button"
            class="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100"
            @click="$emit('show-identity-conflicts')"
          >
            <svg
              class="h-3.5 w-3.5 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01M12 5.25c3.727 0 6.75 3.023 6.75 6.75S15.727 18.75 12 18.75 5.25 15.727 5.25 12 8.273 5.25 12 5.25z"
              />
            </svg>
            <span>{{ t('billing.users.identityConflictChip') }}</span>
            <span class="rounded-full bg-white/80 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
              {{ identityConflictCount }}
            </span>
          </button>
          <input
            :value="search"
            type="text"
            class="w-60 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            :placeholder="t('billing.users.searchPlaceholder')"
            @input="$emit('update:search', $event.target.value)"
            @keyup.enter="$emit('refresh')"
          />
          <BaseButton
            variant="outline"
            size="sm"
            :loading="loading"
            @click="$emit('refresh')"
          >
            {{ t('common.refresh') }}
          </BaseButton>
        </div>
      </div>
    </div>

    <div class="w-full p-6">
      <div
        class="mb-4 flex items-center justify-between gap-3 text-sm text-gray-500"
      >
        <span>{{ t('billing.users.totalCount', { count: userCount }) }}</span>
        <span v-if="userPageOverflow" class="text-amber-600">
          {{ t('billing.users.pageOverflowHint') }}
        </span>
      </div>

      <div
        v-if="selectedUserIds.length > 0"
        class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4"
      >
        <div
          class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
        >
          <p class="text-sm font-medium text-blue-900">
            {{
              t('billing.users.selectedCount', {
                count: selectedUserIds.length
              })
            }}
          </p>
          <BaseButton
            variant="outline"
            size="sm"
            @click="$emit('clear-selection')"
          >
            {{ t('billing.users.clearSelection') }}
          </BaseButton>
        </div>
        <div class="grid gap-3 md:grid-cols-[10rem_1fr_auto]">
          <label class="space-y-1">
            <span class="block text-xs font-medium text-blue-800">
              {{ t('billing.users.batchAmount') }}
            </span>
            <input
              :value="batchAmount"
              type="number"
              min="1"
              class="w-full rounded-md border border-blue-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              @input="$emit('update:batchAmount', Number($event.target.value))"
            />
          </label>
          <label class="space-y-1">
            <span class="block text-xs font-medium text-blue-800">
              {{ t('billing.users.batchReason') }}
            </span>
            <input
              :value="batchReason"
              type="text"
              class="w-full rounded-md border border-blue-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              @input="$emit('update:batchReason', $event.target.value)"
            />
          </label>
          <div class="flex items-end">
            <BaseButton
              variant="primary"
              size="sm"
              class="justify-center"
              :loading="batchGranting"
              @click="$emit('batch-grant')"
            >
              {{ t('billing.users.batchTopUp') }}
            </BaseButton>
          </div>
        </div>
      </div>

      <BaseLoading v-if="loading" />
      <div
        v-else-if="users.length === 0"
        class="rounded-lg border border-gray-200 bg-gray-50 py-12 text-center"
      >
        <p class="text-sm text-gray-600">
          {{ t('billing.users.noData') }}
        </p>
      </div>
      <div v-else class="w-full overflow-x-auto rounded-lg border border-gray-200">
        <table class="w-full min-w-[1100px] divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="w-10 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  :aria-label="t('billing.users.selectAll')"
                  :checked="allUsersSelected"
                  @change="$emit('toggle-all')"
                />
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.username') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.email') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.subscriptionStatus') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.subscriptionSource') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.currentPlan') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.availableCredits') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.periodEnd') }}
              </th>
              <th
                class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.actions') }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 bg-white">
            <tr
              v-for="row in users"
              :key="row.id"
              class="cursor-pointer hover:bg-gray-50"
              :class="selectedUserId === row.user_id ? 'bg-blue-50' : ''"
              @click="$emit('open-user', row)"
            >
              <td class="px-4 py-3">
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  :aria-label="t('billing.users.selectAll')"
                  :checked="selectedUserIds.includes(row.user_id)"
                  @click.stop
                  @change="$emit('toggle-user', row.user_id)"
                />
              </td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">
                {{ row.username }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ row.email || '—' }}
              </td>
              <td class="px-4 py-3 text-sm">
                <span
                  class="inline-flex rounded-full px-2 py-1 text-xs font-medium"
                  :class="getStatusClass(row.subscription_status)"
                >
                  {{ formatSubscriptionStatus(row.subscription_status) }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ formatSubscriptionSource(row.provider_key, row.provider_name) }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                <span
                  :class="
                    row.plan_slug
                      ? 'text-gray-600'
                      : 'font-medium text-amber-700'
                  "
                >
                  {{ row.plan_name || t('billing.users.noSubscription') }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm font-medium text-gray-900">
                {{ row.available_credits }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ formatDate(row.period_end) }}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex justify-end gap-2">
                  <BaseButton
                    variant="primary"
                    size="sm"
                    class="whitespace-nowrap"
                    :disabled="isStripeSource(row.provider_key, row.provider_name)"
                    :loading="
                      assigningPlan && assigningPlanUserId === row.user_id
                    "
                    @click.stop="$emit('assign-plan', row)"
                  >
                    {{ t('billing.users.assignPlanAction') }}
                  </BaseButton>
                  <BaseButton
                    variant="outline"
                    size="sm"
                    class="whitespace-nowrap"
                    @click.stop="$emit('grant-user', row)"
                  >
                    {{ t('billing.users.grantAction') }}
                  </BaseButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'
import {
  formatProviderLabel,
  isStripeProvider
} from '../utils/provider'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t, locale } = useI18n()

defineProps({
  allUsersSelected: {
    type: Boolean,
    default: false
  },
  batchAmount: {
    type: Number,
    default: 10
  },
  batchGranting: {
    type: Boolean,
    default: false
  },
  batchReason: {
    type: String,
    default: 'manual_top_up'
  },
  assigningPlan: {
    type: Boolean,
    default: false
  },
  assigningPlanUserId: {
    type: [Number, String, null],
    default: null
  },
  paymentCheckDisabled: {
    type: Boolean,
    default: false
  },
  paymentRecordBackfillDisabled: {
    type: Boolean,
    default: false
  },
  identityConflictCount: {
    type: Number,
    default: 0
  },
  loading: {
    type: Boolean,
    default: false
  },
  selectedUserId: {
    type: [Number, String, null],
    default: null
  },
  selectedUserIds: {
    type: Array,
    default: () => []
  },
  search: {
    type: String,
    default: ''
  },
  userCount: {
    type: Number,
    default: 0
  },
  userPageOverflow: {
    type: Boolean,
    default: false
  },
  users: {
    type: Array,
    default: () => []
  }
})

defineEmits([
  'batch-grant',
  'clear-selection',
  'assign-plan',
  'grant-user',
  'open-user',
  'show-identity-conflicts',
  'payment-check',
  'payment-record-backfill',
  'refresh',
  'toggle-all',
  'toggle-user',
  'update:batchAmount',
  'update:batchReason',
  'update:search'
])

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

function formatSubscriptionSource(providerKey, providerName) {
  return formatProviderLabel(providerKey, providerName, t)
}

function isStripeSource(providerKey, providerName) {
  return isStripeProvider(providerKey, providerName)
}
</script>
