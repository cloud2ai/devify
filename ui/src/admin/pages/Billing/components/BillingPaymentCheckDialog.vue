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
    enter-active-class="transition-all duration-250 ease-out"
    enter-from-class="translate-y-4 scale-95 opacity-0"
    enter-to-class="translate-y-0 scale-100 opacity-100"
    leave-active-class="transition-all duration-150 ease-in"
    leave-from-class="translate-y-0 scale-100 opacity-100"
    leave-to-class="translate-y-4 scale-95 opacity-0"
  >
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <section
        class="w-full max-w-3xl rounded-2xl border border-gray-200 bg-white shadow-2xl"
        role="dialog"
        :aria-label="t('billing.paymentCheck.title')"
      >
        <div
          class="flex items-center justify-between border-b border-gray-200 px-6 py-5"
        >
          <div>
            <h2 class="text-base font-semibold text-gray-900">
              {{ t('billing.paymentCheck.title') }}
            </h2>
            <p class="mt-1 text-sm text-gray-500">
              {{ t('billing.paymentCheck.subtitle') }}
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

        <div class="space-y-6 p-6">
          <section
            v-if="running"
            class="flex min-h-72 flex-col items-center justify-center gap-4 rounded-2xl border border-gray-200 bg-gradient-to-b from-gray-50 to-white px-6 py-12 text-center"
          >
            <div
              class="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-primary-600"
            >
              <svg
                class="h-6 w-6 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
            </div>
            <div>
              <p class="text-base font-semibold text-gray-900">
                {{ t('billing.paymentCheck.loading') }}
              </p>
              <p class="mt-1 text-sm text-gray-500">
                {{ t('billing.paymentCheck.loadingHint') }}
              </p>
            </div>
            <div class="pt-2">
              <BaseButton variant="outline" size="sm" @click="$emit('close')">
                {{ t('common.close') }}
              </BaseButton>
            </div>
          </section>

          <template v-else-if="result">
            <section v-if="providerBlocks.length > 0" class="space-y-4">
              <article
                v-for="provider in providerBlocks"
                :key="provider.key"
                class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm"
                :class="provider.shellClass"
              >
                <header
                  class="border-b border-gray-200/80 bg-gradient-to-r px-5 py-4"
                  :class="provider.headerClass"
                >
                  <div class="flex items-start justify-between gap-4">
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <span
                          class="inline-flex items-center rounded-full border border-gray-200 bg-white/90 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500"
                        >
                          {{ t('billing.paymentCheck.title') }}
                        </span>
                        <h3 class="text-base font-semibold text-gray-900">
                          {{ provider.label }}
                        </h3>
                        <span
                          class="rounded-full px-2.5 py-1 text-xs font-medium"
                          :class="provider.badgeClass"
                        >
                          {{ provider.statusLabel }}
                        </span>
                      </div>
                      <p class="mt-2 text-sm text-gray-600">
                        {{ provider.summaryText }}
                      </p>
                    </div>
                  </div>
                </header>

                <div class="divide-y divide-gray-200">
                  <template v-if="provider.differences.length > 0">
                    <div
                      v-for="item in provider.differences"
                      :key="item.key"
                      class="group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-gray-50/80"
                    >
                      <div
                        class="flex min-w-0 flex-1 items-center gap-3 overflow-x-auto whitespace-nowrap pr-2 text-sm"
                      >
                        <span
                          class="inline-flex h-2.5 w-2.5 shrink-0 rounded-full"
                          :class="item.dotClass"
                        />
                        <span
                          class="inline-flex shrink-0 items-center rounded-full border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-semibold tracking-[0.08em] text-gray-700"
                        >
                          {{ item.userLabel }}
                        </span>
                        <span
                          class="rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em]"
                          :class="item.badgeClass"
                        >
                          {{ item.statusLabel }}
                        </span>
                        <span class="text-gray-300">•</span>
                        <span class="text-gray-600">
                          <span class="text-gray-400"
                            >{{
                              t('billing.paymentCheck.resultLocalStatus')
                            }}:</span
                          >
                          {{ item.localSummary }}
                        </span>
                        <span class="text-gray-300">•</span>
                        <span class="text-gray-600">
                          <span class="text-gray-400"
                            >{{
                              t('billing.paymentCheck.resultRemoteStatus')
                            }}:</span
                          >
                          {{ item.remoteSummary }}
                        </span>
                        <span class="text-gray-300">•</span>
                        <span class="text-gray-500">
                          <span class="text-gray-400"
                            >{{ t('billing.paymentCheck.resultReason') }}:</span
                          >
                          {{ item.reasonLabel }}
                        </span>
                      </div>

                      <BaseButton
                        v-if="item.canSync"
                        variant="outline"
                        size="sm"
                        class="shrink-0"
                        :loading="syncingUserId === item.userId"
                        :disabled="
                          syncingUserId !== null &&
                          syncingUserId !== item.userId
                        "
                        @click="$emit('sync-user', item.userId)"
                      >
                        {{
                          syncingUserId === item.userId
                            ? t('billing.paymentCheck.syncingToLocal')
                            : t('billing.paymentCheck.syncToLocal')
                        }}
                      </BaseButton>
                    </div>
                  </template>
                  <div v-else class="px-5 py-8 text-sm text-gray-500">
                    {{ provider.emptyText }}
                  </div>
                </div>
              </article>
            </section>

            <section
              v-else
              class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
            >
              {{ t('billing.paymentCheck.noDifferences') }}
            </section>

            <div class="flex items-center justify-end gap-3">
              <BaseButton variant="outline" size="sm" @click="$emit('close')">
                {{ t('common.close') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :loading="running"
                @click="$emit('run')"
              >
                {{ t('billing.paymentCheck.rerunAction') }}
              </BaseButton>
            </div>
          </template>

          <template v-else>
            <section class="space-y-3">
              <div>
                <p class="text-sm font-medium text-gray-900">
                  {{ t('billing.paymentCheck.providersLabel') }}
                </p>
                <p class="mt-1 text-xs text-gray-500">
                  {{ t('billing.paymentCheck.providersHint') }}
                </p>
              </div>
              <div
                v-if="providerOptions.length > 0"
                class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4"
              >
                <label
                  v-for="provider in providerOptions"
                  :key="provider.value"
                  class="flex items-start gap-3 rounded-md border border-gray-200 bg-white px-3 py-2"
                >
                  <input
                    :checked="selectedProviders.includes(provider.value)"
                    type="checkbox"
                    class="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    @change="
                      toggleProvider(provider.value, $event.target.checked)
                    "
                  />
                  <div class="min-w-0">
                    <span class="block text-sm font-medium text-gray-900">
                      {{ provider.label }}
                    </span>
                  </div>
                </label>
              </div>
              <div
                v-else
                class="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
              >
                {{ t('billing.paymentCheck.noProviders') }}
              </div>
            </section>

            <div class="flex items-center justify-end gap-3">
              <BaseButton variant="outline" size="sm" @click="$emit('close')">
                {{ t('common.close') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                :disabled="selectedProviders.length === 0"
                @click="$emit('run')"
              >
                {{ t('billing.paymentCheck.runAction') }}
              </BaseButton>
            </div>
          </template>
        </div>
      </section>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  running: {
    type: Boolean,
    default: false
  },
  providerOptions: {
    type: Array,
    default: () => []
  },
  selectedProviders: {
    type: Array,
    default: () => []
  },
  result: {
    type: Object,
    default: null
  },
  syncingUserId: {
    type: [Number, String, null],
    default: null
  }
})

const emit = defineEmits([
  'close',
  'run',
  'sync-user',
  'update:selectedProviders'
])

function normalizeProviderKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
}

function formatProviderLabel(providerKey, fallbackLabel) {
  if (providerKey === 'stripe') return t('billing.paymentCheck.providerStripe')
  if (providerKey === 'platform')
    return t('billing.paymentCheck.providerPlatform')
  return fallbackLabel || providerKey || '-'
}

function getDecisionMeta(statusKey) {
  if (statusKey === 'would_fix') {
    return {
      badgeClass: 'bg-amber-100 text-amber-800',
      dotClass: 'bg-amber-500',
      label: t('billing.paymentCheck.resultWouldFix')
    }
  }
  if (statusKey === 'manual') {
    return {
      badgeClass: 'bg-rose-100 text-rose-700',
      dotClass: 'bg-rose-500',
      label: t('billing.paymentCheck.resultManual')
    }
  }
  if (statusKey === 'skipped') {
    return {
      badgeClass: 'bg-slate-100 text-slate-500',
      dotClass: 'bg-slate-400',
      label: t('billing.paymentCheck.resultSkipped')
    }
  }
  if (statusKey === 'fixed') {
    return {
      badgeClass: 'bg-emerald-100 text-emerald-700',
      dotClass: 'bg-emerald-500',
      label: t('billing.paymentCheck.resultRepaired')
    }
  }
  return {
    badgeClass: 'bg-rose-100 text-rose-700',
    dotClass: 'bg-rose-500',
    label: t('billing.paymentCheck.resultFailed')
  }
}

function getProviderToneFromIssues(differences) {
  if (
    differences.some((item) => normalizeProviderKey(item.decision) === 'error')
  ) {
    return {
      shellClass: 'border-l-4 border-l-rose-500',
      headerClass: 'from-rose-50 via-white to-white'
    }
  }
  if (
    differences.some((item) => {
      const decisionKey = normalizeProviderKey(item.decision)
      return decisionKey === 'manual' || decisionKey === 'would_fix'
    })
  ) {
    return {
      shellClass: 'border-l-4 border-l-amber-400',
      headerClass: 'from-amber-50 via-white to-white'
    }
  }
  if (
    differences.some((item) => normalizeProviderKey(item.decision) === 'fixed')
  ) {
    return {
      shellClass: 'border-l-4 border-l-emerald-500',
      headerClass: 'from-emerald-50 via-white to-white'
    }
  }
  return {
    shellClass: 'border-l-4 border-l-emerald-500',
    headerClass: 'from-emerald-50 via-white to-white'
  }
}

function getProviderStatusFromIssues(differences) {
  if (
    differences.some((item) => normalizeProviderKey(item.decision) === 'error')
  ) {
    return {
      className: 'bg-rose-100 text-rose-700',
      label: t('billing.paymentCheck.resultFailed')
    }
  }
  if (
    differences.some((item) => normalizeProviderKey(item.decision) === 'manual')
  ) {
    return {
      className: 'bg-rose-100 text-rose-700',
      label: t('billing.paymentCheck.resultManual')
    }
  }
  if (
    differences.some(
      (item) => normalizeProviderKey(item.decision) === 'would_fix'
    )
  ) {
    return {
      className: 'bg-amber-100 text-amber-800',
      label: t('billing.paymentCheck.resultWouldFix')
    }
  }
  if (
    differences.some((item) => normalizeProviderKey(item.decision) === 'fixed')
  ) {
    return {
      className: 'bg-emerald-100 text-emerald-700',
      label: t('billing.paymentCheck.resultRepaired')
    }
  }
  return {
    className: 'bg-emerald-100 text-emerald-700',
    label: t('billing.paymentCheck.resultInSync')
  }
}

const providerBlocks = computed(() => {
  const rows = Array.isArray(props.result?.provider_runs)
    ? props.result.provider_runs
    : Array.isArray(props.result?.providers)
      ? props.result.providers
      : []

  return rows.map((item) => {
    const providerKey = normalizeProviderKey(item.provider || item.name)
    const visibleDifferences = Array.isArray(item.differences)
      ? item.differences.filter((difference) => {
          const decisionKey = normalizeProviderKey(difference.decision)
          return !['in_sync', 'skipped', 'fixed'].includes(decisionKey)
        })
      : []
    const tone = getProviderToneFromIssues(visibleDifferences)
    const status = getProviderStatusFromIssues(visibleDifferences)

    const issueCount = visibleDifferences.length

    return {
      key: `${providerKey}-${item.provider || item.name || 'provider'}`,
      label: formatProviderLabel(providerKey, item.provider || item.name),
      badgeClass: status.className,
      statusLabel: status.label,
      shellClass: tone.shellClass,
      headerClass: tone.headerClass,
      summaryText:
        issueCount > 0
          ? t('billing.paymentCheck.resultIssueCount', { count: issueCount })
          : t('billing.paymentCheck.noDifferences'),
      differences: visibleDifferences.map((difference) => {
        const decisionKey = normalizeProviderKey(difference.decision)
        const decision = getDecisionMeta(decisionKey)
        const localSummary = [
          difference.local_status || '-',
          difference.local_plan_slug ? `(${difference.local_plan_slug})` : ''
        ]
          .filter(Boolean)
          .join(' ')
        const remoteSummary = [
          difference.remote_status || '-',
          difference.remote_plan_slug ? `(${difference.remote_plan_slug})` : ''
        ]
          .filter(Boolean)
          .join(' ')

        return {
          key: `${providerKey}-${difference.user_id || difference.customer_id || difference.remote_subscription_id || decisionKey}`,
          userLabel: difference.user_id
            ? `#${difference.user_id} ${difference.username || '-'}`.trim()
            : difference.username || '-',
          userId: difference.user_id,
          canSync:
            providerKey === 'stripe' &&
            decisionKey === 'would_fix' &&
            Boolean(difference.user_id),
          badgeClass: decision.badgeClass,
          dotClass: decision.dotClass,
          statusLabel: decision.label,
          reasonLabel: difference.reason || '-',
          localSummary,
          remoteSummary
        }
      }),
      emptyText: t('billing.paymentCheck.noDifferences')
    }
  })
})

function toggleProvider(provider, checked) {
  const next = checked
    ? [...props.selectedProviders, provider]
    : props.selectedProviders.filter((item) => item !== provider)
  const unique = [...new Set(next)]
  emit('update:selectedProviders', unique)
}
</script>
