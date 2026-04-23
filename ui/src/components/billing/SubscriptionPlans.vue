<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 h-full">
    <h3 class="text-base font-semibold text-gray-900 mb-3">
      {{ t('billing.plans.title') }}
    </h3>

    <div class="space-y-2.5">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="bg-gray-50 rounded-lg border border-gray-200 p-3 hover:border-primary-300 hover:shadow-sm transition-all"
      >
        <div
          class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5"
        >
          <div
            class="flex flex-col sm:flex-row sm:items-center gap-2.5 flex-1 min-w-0"
          >
            <div :class="['flex-shrink-0', PRICE_WIDTH_CLASS]">
              <div class="flex items-baseline justify-start sm:justify-end">
                <span class="text-xl font-bold text-gray-900">
                  {{ plan.monthly_price }}
                </span>
                <span class="text-sm text-gray-500 ml-1">
                  {{ t('billing.plans.perMonth') }}
                </span>
              </div>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h4 class="text-base font-semibold text-gray-900">
                  {{ plan.name }}
                </h4>
                <span
                  v-if="isCurrentPlan(plan)"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
                >
                  {{ t('billing.plans.current') }}
                </span>
              </div>
              <div class="text-xs text-gray-600 mt-1 space-y-0.5">
                <p
                  v-if="plan.metadata"
                  class="flex items-center gap-1 flex-wrap"
                >
                  <span class="whitespace-nowrap"
                    >{{ t('billing.creditsInfo.emailLimit') }}:
                    {{
                      plan.metadata.max_emails_per_period ||
                      plan.credits_per_period
                    }}
                    {{ t('billing.creditsInfo.emails') }}</span
                  >
                  <span class="text-gray-400">·</span>
                  <span class="whitespace-nowrap"
                    >{{ t('billing.creditsInfo.attachmentLimit') }}:
                    {{ plan.metadata.max_attachment_count }}
                    {{ t('billing.creditsInfo.attachments') }}</span
                  >
                </p>
                <p
                  v-if="plan.metadata"
                  class="flex items-center gap-1 flex-wrap"
                >
                  <span class="whitespace-nowrap"
                    >{{ t('billing.creditsInfo.storageQuota') }}:
                    {{
                      formatPlanStorage(plan.metadata.storage_quota_mb)
                    }}</span
                  >
                  <span class="text-gray-400">·</span>
                  <span class="whitespace-nowrap"
                    >{{ t('billing.creditsInfo.retentionPeriod') }}:
                    {{
                      formatPlanRetention(plan.metadata.retention_days)
                    }}</span
                  >
                </p>
              </div>
            </div>
          </div>

          <div class="flex-shrink-0 w-full sm:w-auto">
            <button
              v-if="
                isCurrentPlan(plan) &&
                plan.slug !== 'free' &&
                currentSubscription?.auto_renew === false
              "
              @click="handleResumeClick"
              :disabled="isInternalUser"
              :class="getButtonClass('resume')"
            >
              {{ t('billing.plans.resumeSubscription') }}
            </button>

            <button
              v-else-if="isCurrentPlan(plan) && plan.slug !== 'free'"
              @click="handleManageSubscription"
              :disabled="isInternalUser"
              :class="getButtonClass('cancel')"
            >
              {{ t('billing.plans.cancelSubscription') }}
            </button>

            <button
              v-else-if="isCurrentPlan(plan) && plan.slug === 'free'"
              disabled
              :class="getButtonClass('current')"
            >
              {{ t('billing.plans.currentPlan') }}
            </button>

            <button
              v-else-if="canUpgrade(plan)"
              @click="handleUpgrade(plan)"
              :disabled="upgrading || isInternalUser"
              :class="getButtonClass('upgrade')"
            >
              {{ upgrading ? t('common.loading') : t('billing.plans.upgrade') }}
            </button>

            <button
              v-else-if="canDowngrade(plan)"
              @click="handleDowngradeClick(plan)"
              :disabled="downgrading || isInternalUser"
              :class="getButtonClass('downgrade')"
            >
              {{
                downgrading ? t('common.loading') : t('billing.plans.downgrade')
              }}
            </button>

            <button v-else disabled :class="getButtonClass('unavailable')">
              {{ t('billing.plans.unavailable') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showCancelDialog"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-start justify-center pt-20"
      @click.self="showCancelDialog = false"
    >
      <div
        class="relative mx-auto p-6 border max-w-md w-full shadow-lg rounded-lg bg-white"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ t('billing.cancel.title') }}
          </h3>
          <button
            @click="showCancelDialog = false"
            class="text-gray-400 hover:text-gray-600"
          >
            <svg
              class="w-6 h-6"
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

        <div class="mb-6">
          <p class="text-sm text-gray-700 mb-4">
            {{ t('billing.cancel.confirmMessage') }}
          </p>
          <div class="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
            <div class="flex gap-3">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-yellow-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div class="flex-1 space-y-2">
                <p class="text-sm text-yellow-800">
                  {{ t('billing.cancel.effectiveNote') }}
                </p>
                <p
                  v-if="formattedPeriodEnd"
                  class="text-sm font-medium text-yellow-900"
                >
                  {{
                    t('billing.cancel.availableUntil', {
                      date: formattedPeriodEnd
                    })
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button
            type="button"
            @click="showCancelDialog = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="confirmCancelSubscription"
            :disabled="canceling"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50"
          >
            {{ canceling ? t('common.loading') : t('billing.cancel.confirm') }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showDowngradeDialog"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-start justify-center pt-20"
      @click.self="showDowngradeDialog = false"
    >
      <div
        class="relative mx-auto p-6 border max-w-md w-full shadow-lg rounded-lg bg-white"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ t('billing.downgrade.title') }}
          </h3>
          <button
            @click="showDowngradeDialog = false"
            class="text-gray-400 hover:text-gray-600"
          >
            <svg
              class="w-6 h-6"
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

        <div class="mb-6">
          <p class="text-sm text-gray-700 mb-4">
            {{
              t('billing.downgrade.confirmMessage', {
                plan: selectedDowngradePlan?.name || ''
              })
            }}
          </p>
          <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <div class="flex gap-3">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div class="flex-1 space-y-2">
                <p class="text-sm text-blue-800">
                  {{ t('billing.downgrade.effectiveNote') }}
                </p>
                <p
                  v-if="formattedPeriodEnd"
                  class="text-sm font-medium text-blue-900"
                >
                  {{
                    t('billing.downgrade.availableUntil', {
                      date: formattedPeriodEnd
                    })
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button
            type="button"
            @click="showDowngradeDialog = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="confirmDowngrade"
            :disabled="downgrading"
            class="px-4 py-2 text-sm font-medium text-white bg-orange-600 hover:bg-orange-700 rounded-md disabled:opacity-50"
          >
            {{
              downgrading ? t('common.loading') : t('billing.downgrade.confirm')
            }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showResumeDialog"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-start justify-center pt-20"
      @click.self="showResumeDialog = false"
    >
      <div
        class="relative mx-auto p-6 border max-w-md w-full shadow-lg rounded-lg bg-white"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ t('billing.resume.title') }}
          </h3>
          <button
            @click="showResumeDialog = false"
            class="text-gray-400 hover:text-gray-600"
          >
            <svg
              class="w-6 h-6"
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

        <div class="mb-6">
          <p class="text-sm text-gray-700 mb-4">
            {{ t('billing.resume.confirmMessage') }}
          </p>
          <div class="bg-green-50 rounded-lg p-4 border border-green-200">
            <div class="flex gap-3">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div class="flex-1 space-y-2">
                <p class="text-sm text-green-800">
                  {{ t('billing.resume.effectiveNote') }}
                </p>
                <p
                  v-if="formattedPeriodEnd"
                  class="text-sm font-medium text-green-900"
                >
                  {{
                    t('billing.resume.nextBillingDate', {
                      date: formattedPeriodEnd
                    })
                  }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <button
            type="button"
            @click="showResumeDialog = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="confirmResumeSubscription"
            :disabled="resuming"
            class="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md disabled:opacity-50"
          >
            {{ resuming ? t('common.loading') : t('billing.resume.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Updated with date display in dialogs
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import billingApi from '@/api/billing'

const { t, locale } = useI18n()
const toast = useToast()

const props = defineProps({
  currentSubscription: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'subscription-updated',
  'operation-success',
  'operation-error'
])

const plans = ref([])
const upgrading = ref(false)
const showCancelDialog = ref(false)
const canceling = ref(false)
const showDowngradeDialog = ref(false)
const downgrading = ref(false)
const selectedDowngradePlan = ref(null)
const showResumeDialog = ref(false)
const resuming = ref(false)

const currentPlanSlug = computed(() => {
  return props.currentSubscription?.plan_slug || 'free'
})

const isInternalUser = computed(() => {
  return (
    props.currentSubscription?.plan_slug === 'internal' ||
    props.currentSubscription?.plan_is_internal ||
    props.currentSubscription?.plan?.is_internal
  )
})

const formattedPeriodEnd = computed(() => {
  if (!props.currentSubscription?.current_period_end) return ''

  const date = new Date(props.currentSubscription.current_period_end)
  const dateLocale = locale.value === 'zh-CN' ? zhCN : enUS

  if (locale.value === 'zh-CN') {
    return format(date, 'yyyy年M月d日', { locale: dateLocale })
  } else {
    return format(date, 'MMM dd, yyyy', { locale: dateLocale })
  }
})

const planOrder = { free: 0, starter: 1, standard: 2, pro: 3 }

const BUTTON_WIDTH_CLASS = 'w-full sm:w-40'
const PRICE_WIDTH_CLASS = 'w-auto sm:w-36'

const BASE_BUTTON_CLASS =
  'px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap flex items-center justify-center'

const BUTTON_STYLES = {
  resume:
    'text-green-700 bg-green-50 border border-green-200 hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed',
  cancel:
    'text-red-700 bg-red-50 border border-red-200 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed',
  current: 'text-gray-600 bg-gray-100 cursor-not-allowed',
  upgrade:
    'text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed',
  downgrade:
    'text-orange-700 bg-orange-50 border border-orange-200 hover:bg-orange-100 disabled:opacity-50 disabled:cursor-not-allowed',
  unavailable: 'text-gray-400 bg-gray-100 cursor-not-allowed'
}

const isCanceledButActive = computed(() => {
  return (
    props.currentSubscription &&
    props.currentSubscription.status === 'active' &&
    props.currentSubscription.auto_renew === false
  )
})

function isCurrentPlan(plan) {
  return plan.slug === currentPlanSlug.value
}

function getButtonClass(type) {
  return `${BUTTON_WIDTH_CLASS} ${BASE_BUTTON_CLASS} ${BUTTON_STYLES[type]}`
}

function canUpgrade(plan) {
  if (isInternalUser.value) {
    return false
  }
  const currentOrder = planOrder[currentPlanSlug.value] || 0
  const targetOrder = planOrder[plan.slug] || 0
  return targetOrder > currentOrder
}

function canDowngrade(plan) {
  if (isInternalUser.value) {
    return false
  }
  if (isCanceledButActive.value) {
    return false
  }
  const currentOrder = planOrder[currentPlanSlug.value] || 0
  const targetOrder = planOrder[plan.slug] || 0
  return targetOrder < currentOrder && plan.slug !== 'free'
}

function formatPlanStorage(storageMb) {
  if (!storageMb) return '-'
  if (storageMb >= 1024) {
    return `${(storageMb / 1024).toFixed(0)} GB`
  }
  return `${storageMb} MB`
}

function formatPlanRetention(retentionDays) {
  if (retentionDays === null || retentionDays === undefined) {
    return t('billing.creditsInfo.retentionNotSet')
  }
  if (retentionDays === -1) {
    return t('billing.creditsInfo.retentionPermanent')
  }
  if (retentionDays >= 365) {
    const years = Math.floor(retentionDays / 365)
    if (years === 1) {
      return locale.value === 'zh-CN' ? '1年' : '1 year'
    }
    return t('billing.creditsInfo.retentionYears', { years })
  }
  return t('billing.creditsInfo.retentionDays', { days: retentionDays })
}

async function fetchPlans() {
  try {
    const response = await billingApi.getPlans()
    const plansData = response.data.data || response.data
    plans.value = plansData
  } catch (error) {
    console.error('Failed to fetch plans:', error)
  }
}

async function handleUpgrade(plan) {
  if (isInternalUser.value) {
    return
  }
  if (!plan.stripe_price_id) {
    toast.showWarning(t('billing.plans.stripeNotConfigured'))
    return
  }

  upgrading.value = true

  try {
    const response = await billingApi.createCheckoutSession(
      plan.stripe_price_id
    )
    const responseData = response.data.data || response.data

    if (responseData.checkout_url) {
      window.location.href = responseData.checkout_url
    } else {
      console.error('No checkout URL in response:', responseData)
      emit('operation-error', t('billing.plans.upgradeFailed'))
    }
  } catch (error) {
    console.error('Failed to create checkout session:', error)
    emit('operation-error', t('billing.plans.upgradeFailed'))
  } finally {
    upgrading.value = false
  }
}

function handleManageSubscription() {
  if (isInternalUser.value) {
    return
  }
  showCancelDialog.value = true
}

function handleDowngradeClick(plan) {
  if (isInternalUser.value) {
    return
  }
  selectedDowngradePlan.value = plan
  showDowngradeDialog.value = true
}

async function confirmDowngrade() {
  if (isInternalUser.value) {
    return
  }
  if (!selectedDowngradePlan.value) return

  downgrading.value = true
  try {
    await billingApi.scheduleDowngrade(
      selectedDowngradePlan.value.stripe_price_id
    )
    showDowngradeDialog.value = false
    emit('operation-success', 'downgrade')
    emit('subscription-updated')
  } catch (error) {
    console.error('Failed to schedule downgrade:', error)
    showDowngradeDialog.value = false
    emit('operation-error', t('billing.downgrade.failed'))
  } finally {
    downgrading.value = false
  }
}

async function confirmCancelSubscription() {
  if (isInternalUser.value) {
    return
  }
  if (!props.currentSubscription) {
    return
  }

  canceling.value = true

  try {
    await billingApi.cancelSubscription(props.currentSubscription.id)
    showCancelDialog.value = false
    emit('operation-success', 'cancel')
    emit('subscription-updated')
  } catch (error) {
    console.error('Failed to cancel subscription:', error)
    showCancelDialog.value = false
    emit('operation-error', t('billing.plans.cancelFailed'))
  } finally {
    canceling.value = false
  }
}

function handleResumeClick() {
  if (isInternalUser.value) {
    return
  }
  showResumeDialog.value = true
}

async function confirmResumeSubscription() {
  if (isInternalUser.value) {
    return
  }
  if (!props.currentSubscription) {
    return
  }

  resuming.value = true

  try {
    await billingApi.resumeSubscription(props.currentSubscription.id)
    showResumeDialog.value = false
    emit('operation-success', 'resume')
    emit('subscription-updated')
  } catch (error) {
    console.error('Failed to resume subscription:', error)
    showResumeDialog.value = false
    emit('operation-error', t('billing.plans.resumeFailed'))
  } finally {
    resuming.value = false
  }
}

onMounted(() => {
  fetchPlans()
})
</script>
