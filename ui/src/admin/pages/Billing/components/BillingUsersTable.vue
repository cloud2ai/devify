<template>
  <section class="rounded-lg border border-gray-200 bg-white shadow-sm">
    <div
      class="flex items-center justify-between gap-3 border-b border-gray-200 px-6 py-5"
    >
      <div>
        <h2 class="text-base font-semibold text-gray-900">
          {{ t('billing.sections.users') }}
        </h2>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('billing.sections.usersDesc') }}
        </p>
      </div>
      <div class="flex items-center gap-2">
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

    <div class="p-6">
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
      <div v-else class="overflow-x-auto rounded-lg border border-gray-200">
        <table class="min-w-full divide-y divide-gray-200">
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
                {{ t('billing.users.availableCredits') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.baseCredits') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.bonusCredits') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.consumedCredits') }}
              </th>
              <th
                class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
              >
                {{ t('billing.users.plan') }}
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
              <td class="px-4 py-3 text-sm text-gray-900">
                {{ row.available_credits }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ row.base_credits }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ row.bonus_credits }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ row.consumed_credits }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ row.plan_name || '—' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600">
                {{ formatDate(row.period_end) }}
              </td>
              <td class="px-4 py-3 text-right">
                <BaseButton
                  variant="outline"
                  size="sm"
                  class="whitespace-nowrap"
                  @click.stop="$emit('grant-user', row)"
                >
                  {{ t('billing.users.grantAction') }}
                </BaseButton>
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
  'grant-user',
  'open-user',
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
</script>
