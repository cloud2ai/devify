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
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-4xl flex-col bg-white shadow-xl"
      role="region"
      :aria-label="t('billing.audit.detailTitle')"
    >
      <div
        class="flex items-center justify-between border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4"
      >
        <div class="min-w-0">
          <h2 class="truncate text-lg font-semibold text-gray-900">
            {{ log?.action_type || t('billing.audit.detailTitle') }}
          </h2>
          <p class="mt-1 truncate text-xs text-gray-500">
            {{ log?.event_key || '—' }}
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
        <BaseLoading v-if="loading" />

        <template v-else-if="log">
          <div class="space-y-6">
            <section class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div class="flex flex-wrap items-center gap-2">
                <span
                  class="inline-flex rounded-full px-3 py-1 text-xs font-semibold"
                  :class="actionBadgeClass(log.action_type)"
                >
                  {{ formatActionType(log.action_type) }}
                </span>
                <span
                  class="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700"
                >
                  {{ formatSource(log.source) }}
                </span>
                <span class="text-xs text-gray-500">
                  {{ formatDate(log.created_at) }}
                </span>
              </div>

              <dl class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.actor') }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-gray-900">
                    {{ displayActor(log) }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.targetUser') }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-gray-900">
                    {{ displayTargetUser(log) }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.resource') }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-gray-900">
                    {{ displayResource(log) }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.ipAddress') }}
                  </dt>
                  <dd class="mt-1 text-sm font-medium text-gray-900">
                    {{ log.ip_address || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.userAgent') }}
                  </dt>
                  <dd class="mt-1 break-all text-sm font-medium text-gray-900">
                    {{ log.user_agent || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {{ t('billing.audit.eventKey') }}
                  </dt>
                  <dd class="mt-1 break-all font-mono text-xs text-gray-700">
                    {{ log.event_key || '—' }}
                  </dd>
                </div>
              </dl>
            </section>

            <section
              v-for="panel in diffPanels"
              :key="panel.key"
              class="rounded-2xl border border-gray-200 bg-white shadow-sm"
            >
              <div class="border-b border-gray-200 px-5 py-4">
                <h3 class="text-sm font-semibold text-gray-900">
                  {{ panel.title }}
                </h3>
              </div>
              <div class="p-5">
                <div
                  v-if="isEmptyJson(panel.value)"
                  class="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500"
                >
                  {{ t('billing.audit.noJsonData') }}
                </div>
                <pre
                  v-else
                  class="overflow-x-auto rounded-xl border border-gray-200 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-100 shadow-inner"
                >{{ formatJson(panel.value) }}</pre>
              </div>
            </section>
          </div>
        </template>
      </div>
    </aside>
  </transition>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t, locale } = useI18n()

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  open: {
    type: Boolean,
    default: false
  },
  log: {
    type: Object,
    default: null
  }
})

defineEmits(['close'])

const diffPanels = computed(() => [
  {
    key: 'before',
    title: t('billing.audit.beforeData'),
    value: props.log?.before_data || {}
  },
  {
    key: 'after',
    title: t('billing.audit.afterData'),
    value: props.log?.after_data || {}
  },
  {
    key: 'context',
    title: t('billing.audit.context'),
    value: props.log?.context || {}
  }
])

const actionTypeLabels = {
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

const sourceLabels = {
  admin_api: 'billing.audit.sources.adminApi',
  user_api: 'billing.audit.sources.userApi',
  webhook: 'billing.audit.sources.webhook',
  system_task: 'billing.audit.sources.systemTask',
  system: 'billing.audit.sources.system'
}

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

function formatJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}

function isEmptyJson(value) {
  if (!value) return true
  return Object.keys(value).length === 0
}

function formatActionType(value) {
  if (!value) return t('common.status.unknown')
  const labelKey = actionTypeLabels[value]
  return labelKey ? t(labelKey) : value
}

function formatSource(value) {
  if (!value) return t('common.status.unknown')
  const labelKey = sourceLabels[value]
  return labelKey ? t(labelKey) : value
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
</script>
