<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 class="text-lg font-semibold text-gray-900">
            {{ t('billing.auditPageTitle') }}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {{ t('billing.auditPageSubtitle') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <BaseButton
            variant="outline"
            size="sm"
            :loading="loading"
            @click="loadLogs"
          >
            {{ t('common.refresh') }}
          </BaseButton>
          <BaseButton variant="outline" size="sm" @click="resetFilters">
            {{ t('billing.audit.resetFilters') }}
          </BaseButton>
        </div>
      </div>

      <section class="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div class="border-b border-gray-200 px-6 py-5">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 class="text-base font-semibold text-gray-900">
                {{ t('billing.audit.filterTitle') }}
              </h2>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('billing.audit.filterSubtitle') }}
              </p>
            </div>
            <span class="text-sm text-gray-500">
              {{ t('billing.audit.totalCount', { count: totalCount }) }}
            </span>
          </div>

          <div class="mt-5 grid gap-3 lg:grid-cols-12">
            <label class="space-y-1 lg:col-span-3">
              <span class="block text-xs font-semibold uppercase tracking-wider text-gray-500">
                {{ t('billing.audit.filters.user') }}
              </span>
              <input
                v-model="filters.user"
                type="text"
                class="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                :placeholder="t('billing.audit.filters.userPlaceholder')"
                @keyup.enter="applyFilters"
              />
            </label>

            <label class="space-y-1 lg:col-span-3">
              <span class="block text-xs font-semibold uppercase tracking-wider text-gray-500">
                {{ t('billing.audit.filters.actionType') }}
              </span>
              <select
                v-model="filters.action_type"
                class="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="applyFilters"
              >
                <option value="">{{ t('billing.audit.filters.allActions') }}</option>
                <option
                  v-for="option in actionTypeOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </label>

            <label class="space-y-1 lg:col-span-3">
              <span class="block text-xs font-semibold uppercase tracking-wider text-gray-500">
                {{ t('billing.audit.filters.source') }}
              </span>
              <select
                v-model="filters.source"
                class="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="applyFilters"
              >
                <option value="">{{ t('billing.audit.filters.allSources') }}</option>
                <option
                  v-for="option in sourceOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </label>

            <label class="space-y-1 lg:col-span-1">
              <span class="block text-xs font-semibold uppercase tracking-wider text-gray-500">
                {{ t('billing.audit.filters.startDate') }}
              </span>
              <input
                v-model="filters.start_date"
                type="date"
                :max="filters.end_date || undefined"
                class="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="applyFilters"
              />
            </label>

            <label class="space-y-1 lg:col-span-1">
              <span class="block text-xs font-semibold uppercase tracking-wider text-gray-500">
                {{ t('billing.audit.filters.endDate') }}
              </span>
              <input
                v-model="filters.end_date"
                type="date"
                :min="filters.start_date || undefined"
                class="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="applyFilters"
              />
            </label>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-gray-500">
              {{ t('billing.audit.filterHint') }}
            </p>
            <div class="flex items-center gap-2">
              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                @click="applyFilters"
              >
                {{ t('billing.audit.applyFilters') }}
              </BaseButton>
            </div>
          </div>
        </div>

        <BaseLoading v-if="loading && logs.length === 0" class="p-6" />

        <div v-else-if="logs.length === 0" class="p-6">
          <div class="rounded-2xl border border-gray-200 bg-gray-50 py-14 text-center">
            <p class="text-sm text-gray-600">
              {{ t('billing.audit.noData') }}
            </p>
          </div>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.time') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.action') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.source') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.actor') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.targetUser') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.resource') }}
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
                  {{ t('billing.audit.ipAddress') }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 bg-white">
              <tr
                v-for="log in logs"
                :key="log.id"
                class="cursor-pointer transition-colors hover:bg-gray-50"
                @click="openDetail(log)"
              >
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {{ formatDate(log.created_at) }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm">
                  <span
                    class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold"
                    :class="actionBadgeClass(log.action_type)"
                  >
                    {{ formatActionType(log.action_type) }}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm">
                  <span class="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                    {{ formatSource(log.source) }}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {{ displayActor(log) }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {{ displayTargetUser(log) }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  <span class="font-mono text-xs">
                    {{ displayResource(log) }}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  <span class="font-mono text-xs">
                    {{ log.ip_address || '—' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-if="totalCount > 0"
          class="border-t border-gray-200 px-6 py-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-gray-600">
              {{ paginationSummary }}
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <label class="text-sm text-gray-600">
                {{ t('common.pagination.itemsPerPage') }}:
              </label>
              <select
                v-model.number="pageSize"
                class="rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="changePageSize"
              >
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
              <BaseButton
                variant="outline"
                size="sm"
                :disabled="page <= 1"
                @click="goToPreviousPage"
              >
                {{ t('common.pagination.previous') }}
              </BaseButton>
              <BaseButton
                variant="outline"
                size="sm"
                :disabled="page >= totalPages"
                @click="goToNextPage"
              >
                {{ t('common.pagination.next') }}
              </BaseButton>
            </div>
          </div>
        </div>
      </section>

      <BillingAuditLogDrawer
        :loading="detailLoading"
        :log="selectedLog"
        :open="detailOpen"
        @close="closeDetail"
      />
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import { billingAdminApi } from '@/admin/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BillingAuditLogDrawer from './components/BillingAuditLogDrawer.vue'

const { t, locale } = useI18n()
const toast = useToast()

const loading = ref(true)
const detailLoading = ref(false)
const logs = ref([])
const totalCount = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailOpen = ref(false)
const selectedLog = ref(null)

const filters = reactive({
  user: '',
  action_type: '',
  source: '',
  start_date: '',
  end_date: ''
})

const actionTypeOptions = computed(() => [
  {
    value: 'subscription.assign',
    label: t('billing.audit.actionTypes.subscriptionAssign')
  },
  {
    value: 'subscription.create',
    label: t('billing.audit.actionTypes.subscriptionCreate')
  },
  {
    value: 'subscription.cancel',
    label: t('billing.audit.actionTypes.subscriptionCancel')
  },
  {
    value: 'subscription.resume',
    label: t('billing.audit.actionTypes.subscriptionResume')
  },
  {
    value: 'credits.grant',
    label: t('billing.audit.actionTypes.creditsGrant')
  },
  {
    value: 'credits.batch_grant',
    label: t('billing.audit.actionTypes.creditsBatchGrant')
  },
  {
    value: 'plan.create',
    label: t('billing.audit.actionTypes.planCreate')
  },
  {
    value: 'plan.update',
    label: t('billing.audit.actionTypes.planUpdate')
  },
  {
    value: 'plan.delete',
    label: t('billing.audit.actionTypes.planDelete')
  },
  {
    value: 'billing_config.update',
    label: t('billing.audit.actionTypes.configUpdate')
  }
])

const sourceOptions = computed(() => [
  { value: 'admin_api', label: t('billing.audit.sources.adminApi') },
  { value: 'user_api', label: t('billing.audit.sources.userApi') },
  { value: 'webhook', label: t('billing.audit.sources.webhook') },
  { value: 'system_task', label: t('billing.audit.sources.systemTask') },
  { value: 'system', label: t('billing.audit.sources.system') }
])

const totalPages = computed(() =>
  totalCount.value > 0 ? Math.ceil(totalCount.value / pageSize.value) : 0
)

const paginationSummary = computed(() => {
  if (totalCount.value === 0) return ''
  const from = (page.value - 1) * pageSize.value + 1
  const to = Math.min(page.value * pageSize.value, totalCount.value)
  return t('common.pagination.showing', {
    from,
    to,
    total: totalCount.value
  })
})

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

function formatActionType(value) {
  if (!value) return t('common.status.unknown')
  const map = {
    'subscription.assign': 'billing.audit.actionTypes.subscriptionAssign',
    'subscription.create': 'billing.audit.actionTypes.subscriptionCreate',
    'subscription.cancel': 'billing.audit.actionTypes.subscriptionCancel',
    'subscription.resume': 'billing.audit.actionTypes.subscriptionResume',
    'credits.grant': 'billing.audit.actionTypes.creditsGrant',
    'credits.batch_grant': 'billing.audit.actionTypes.creditsBatchGrant',
    'plan.create': 'billing.audit.actionTypes.planCreate',
    'plan.update': 'billing.audit.actionTypes.planUpdate',
    'plan.delete': 'billing.audit.actionTypes.planDelete',
    'billing_config.update': 'billing.audit.actionTypes.configUpdate',
    'webhook.subscription.created':
      'billing.audit.actionTypes.webhookSubscriptionCreated',
    'webhook.subscription.updated':
      'billing.audit.actionTypes.webhookSubscriptionUpdated',
    'webhook.subscription.deleted':
      'billing.audit.actionTypes.webhookSubscriptionDeleted',
    'webhook.invoice.payment_succeeded':
      'billing.audit.actionTypes.webhookPaymentSucceeded',
    'webhook.invoice.payment_failed':
      'billing.audit.actionTypes.webhookPaymentFailed',
    'system.renew_expired_credits':
      'billing.audit.actionTypes.systemRenewCredits',
    'system.downgrade_failed_paid_subscription':
      'billing.audit.actionTypes.systemDowngradeSubscription'
  }
  return map[value] ? t(map[value]) : value
}

function formatSource(value) {
  if (!value) return t('common.status.unknown')
  const map = {
    admin_api: 'billing.audit.sources.adminApi',
    user_api: 'billing.audit.sources.userApi',
    webhook: 'billing.audit.sources.webhook',
    system_task: 'billing.audit.sources.systemTask',
    system: 'billing.audit.sources.system'
  }
  return map[value] ? t(map[value]) : value
}

function actionBadgeClass(value) {
  if (!value) return 'bg-gray-100 text-gray-700'
  if (value.startsWith('credits.')) return 'bg-emerald-100 text-emerald-800'
  if (value.startsWith('subscription.')) return 'bg-blue-100 text-blue-800'
  if (value.startsWith('plan.')) return 'bg-violet-100 text-violet-800'
  if (value.startsWith('webhook.')) return 'bg-amber-100 text-amber-800'
  if (value.startsWith('system.')) return 'bg-slate-100 text-slate-700'
  if (value === 'billing_config.update')
    return 'bg-indigo-100 text-indigo-800'
  return 'bg-gray-100 text-gray-700'
}

function displayActor(log) {
  return (
    log?.actor_username ||
    log?.actor_name ||
    (log?.actor ? String(log.actor) : '—')
  )
}

function displayTargetUser(log) {
  return (
    log?.target_user_username ||
    log?.target_username ||
    (log?.target_user ? String(log.target_user) : '—')
  )
}

function displayResource(log) {
  const parts = []
  if (log?.resource_type) parts.push(log.resource_type)
  if (log?.resource_id) parts.push(`#${log.resource_id}`)
  return parts.length ? parts.join(' ') : '—'
}

async function loadLogs() {
  loading.value = true
  try {
    const data = await billingAdminApi.getAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      user: filters.user.trim() || undefined,
      action_type: filters.action_type || undefined,
      source: filters.source || undefined,
      start_date: filters.start_date || undefined,
      end_date: filters.end_date || undefined
    })
    logs.value = data.results || []
    totalCount.value = data.count || 0
    if (page.value > totalPages.value && totalPages.value > 0) {
      page.value = totalPages.value
      await loadLogs()
    }
  } catch (error) {
    console.error('Failed to load billing audit logs:', error)
    logs.value = []
    totalCount.value = 0
    toast.showError(t('billing.audit.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  page.value = 1
  await loadLogs()
}

async function changePageSize() {
  page.value = 1
  await loadLogs()
}

async function goToPreviousPage() {
  if (page.value <= 1) return
  page.value -= 1
  await loadLogs()
}

async function goToNextPage() {
  if (page.value >= totalPages.value) return
  page.value += 1
  await loadLogs()
}

function resetFilters() {
  filters.user = ''
  filters.action_type = ''
  filters.source = ''
  filters.start_date = ''
  filters.end_date = ''
  page.value = 1
  loadLogs()
}

function openDetail(log) {
  selectedLog.value = log
  detailOpen.value = true
}

function closeDetail() {
  detailOpen.value = false
}

onMounted(() => {
  loadLogs()
})
</script>
