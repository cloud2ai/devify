<template>
  <div
    class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 h-full flex flex-col"
  >
    <h3 class="text-base font-semibold text-gray-900 mb-3">
      {{ t('billing.currentSubscription.title') }}
    </h3>

    <div v-if="subscription || credits" class="flex-1 flex flex-col space-y-3">
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <h4 class="text-lg font-semibold text-gray-900">
            {{ subscription ? subscription.plan_name : 'Free Plan' }}
          </h4>
          <span
            v-if="subscription"
            :class="[
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              getStatusIconClass(subscription.status)
            ]"
          >
            <svg
              v-if="subscription.status === 'active'"
              class="w-3 h-3"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clip-rule="evenodd"
              />
            </svg>
            <svg
              v-else-if="subscription.status === 'canceled'"
              class="w-2 h-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <circle cx="10" cy="10" r="10" />
            </svg>
            <svg
              v-else-if="subscription.status === 'past_due'"
              class="w-3 h-3"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fill-rule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
            <svg v-else class="w-2 h-2" fill="currentColor" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="10" />
            </svg>
            <span>{{ getStatusText(subscription.status) }}</span>
          </span>
          <span
            v-else
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700"
          >
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clip-rule="evenodd"
              />
            </svg>
            <span>{{ t('billing.status.active') }}</span>
          </span>
        </div>

        <p v-if="subscription" class="text-xs text-gray-600">
          {{ t('billing.currentSubscription.provider') }}:
          {{ subscription.provider_name }}
        </p>
        <p v-else class="text-xs text-gray-600">
          {{ t('billing.currentSubscription.freePlanDesc') }}
        </p>
      </div>

      <div class="space-y-1.5 flex-grow">
        <div class="flex justify-between items-center">
          <span class="text-xs text-gray-600">
            {{ t('billing.currentSubscription.periodStart') }}
          </span>
          <span class="text-xs font-medium text-gray-900">
            {{
              subscription ? formatDate(subscription.current_period_start) : '-'
            }}
          </span>
        </div>

        <div class="flex justify-between items-center">
          <span class="text-xs text-gray-600">
            {{ t('billing.currentSubscription.periodEnd') }}
          </span>
          <span class="text-xs font-medium text-gray-900">
            {{
              subscription ? formatDate(subscription.current_period_end) : '-'
            }}
          </span>
        </div>

        <div class="flex justify-between items-center">
          <span class="text-xs text-gray-600">
            {{ t('billing.currentSubscription.remaining') }}
          </span>
          <span class="text-xs font-medium text-primary-600">
            {{
              subscription && daysRemaining !== null
                ? t('billing.currentSubscription.daysRemainingValue', {
                    days: daysRemaining
                  })
                : '-'
            }}
          </span>
        </div>

        <div class="flex justify-between items-center">
          <span class="text-xs text-gray-600">
            {{ t('billing.currentSubscription.autoRenew') }}
          </span>
          <span
            :class="[
              'text-xs font-medium',
              subscription && subscription.auto_renew
                ? 'text-green-600'
                : 'text-gray-600'
            ]"
          >
            {{
              subscription
                ? subscription.auto_renew
                  ? t('common.yes')
                  : t('common.no')
                : '-'
            }}
          </span>
        </div>
      </div>

      <div v-if="credits" class="pt-3">
        <div
          class="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg p-2.5"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-gray-700">
              {{ t('billing.currentSubscription.creditsUsage') }}
            </span>
            <span class="text-sm font-semibold text-primary-700">
              {{ credits.available_credits }} / {{ credits.total_credits }}
            </span>
          </div>

          <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
            <div
              class="bg-primary-600 h-1.5 rounded-full transition-all"
              :style="{ width: `${creditsPercentage}%` }"
            />
          </div>

          <div class="p-2 bg-white rounded-lg border border-gray-200 text-xs">
            <div class="flex items-center gap-1.5 p-1 mb-2">
              <svg
                class="w-3.5 h-3.5 text-primary-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fill-rule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clip-rule="evenodd"
                />
              </svg>
              <p class="font-medium text-gray-900">
                {{ t('billing.creditsInfo.title') }}
              </p>
            </div>

            <div class="space-y-1.5">
              <p class="text-gray-600 px-1">
                {{ t('billing.creditsInfo.description') }}
              </p>
              <div class="border-t border-gray-100 pt-2 space-y-1.5">
                <div class="flex justify-between">
                  <span class="text-gray-600">{{
                    t('billing.creditsInfo.emailLimit')
                  }}</span>
                  <span class="font-medium text-gray-900"
                    >{{
                      planMetadata?.max_emails_per_period ||
                      planMetadata?.credits_per_period ||
                      '-'
                    }}
                    {{ t('billing.creditsInfo.emails') }}</span
                  >
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">{{
                    t('billing.creditsInfo.attachmentLimit')
                  }}</span>
                  <span class="font-medium text-gray-900"
                    >{{ planMetadata?.max_attachment_count || '-' }}
                    {{ t('billing.creditsInfo.attachments') }}</span
                  >
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">{{
                    t('billing.creditsInfo.storageQuota')
                  }}</span>
                  <span class="font-medium text-gray-900">{{
                    formatStorage(planMetadata?.storage_quota_mb)
                  }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">{{
                    t('billing.creditsInfo.retentionPeriod')
                  }}</span>
                  <span class="font-medium text-gray-900">{{
                    formatRetention(planMetadata?.retention_days)
                  }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-4">
      <svg
        class="mx-auto h-10 w-10 text-gray-400"
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
      <p class="mt-2 text-sm text-gray-500">
        {{ t('common.loading') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format, differenceInDays } from 'date-fns'
import { usePreferencesStore } from '@/store/preferences'

const { t } = useI18n()
const preferencesStore = usePreferencesStore()

const props = defineProps({
  subscription: {
    type: Object,
    default: null
  },
  credits: {
    type: Object,
    default: null
  }
})

const planMetadata = computed(() => {
  return (
    props.subscription?.plan_metadata || props.credits?.plan_metadata || null
  )
})

const creditsPercentage = computed(() => {
  if (!props.credits || !props.credits.total_credits) {
    return 0
  }
  return Math.round(
    (props.credits.available_credits / props.credits.total_credits) * 100
  )
})

function getStatusIconClass(status) {
  const classes = {
    active: 'bg-green-100 text-green-700',
    canceled: 'bg-gray-100 text-gray-600',
    trialing: 'bg-blue-100 text-blue-700',
    past_due: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-600'
}

function getStatusText(status) {
  const texts = {
    active: t('billing.status.active'),
    canceled: t('billing.status.canceled'),
    trialing: t('billing.status.trialing'),
    past_due: t('billing.status.pastDue')
  }
  return texts[status] || status
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)

  const isZhCN = preferencesStore.currentLanguage === 'zh-CN'

  if (isZhCN) {
    return format(date, 'yyyy年M月d日')
  } else {
    return format(date, 'MMM dd, yyyy')
  }
}

const daysRemaining = computed(() => {
  if (!props.subscription || !props.subscription.current_period_end) {
    return null
  }

  const endDate = new Date(props.subscription.current_period_end)
  const today = new Date()
  const days = differenceInDays(endDate, today)

  return days > 0 ? days : 0
})

function formatStorage(storageMb) {
  if (!storageMb) return '-'
  if (storageMb >= 1024) {
    return `${(storageMb / 1024).toFixed(0)} GB`
  }
  return `${storageMb} MB`
}

function formatRetention(retentionDays) {
  if (retentionDays === null || retentionDays === undefined) {
    return t('billing.creditsInfo.retentionNotSet')
  }
  if (retentionDays === -1) {
    return t('billing.creditsInfo.retentionPermanent')
  }
  if (retentionDays >= 365) {
    const years = Math.floor(retentionDays / 365)
    if (years === 1) {
      return preferencesStore.currentLanguage === 'zh-CN' ? '1年' : '1 year'
    }
    return t('billing.creditsInfo.retentionYears', { years })
  }
  return t('billing.creditsInfo.retentionDays', { days: retentionDays })
}
</script>
