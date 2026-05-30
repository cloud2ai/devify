<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div
        class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
      >
        <div>
          <h1 class="text-lg font-semibold text-gray-900">
            {{ t('billing.usersPageTitle') }}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {{ t('billing.usersPageSubtitle') }}
          </p>
        </div>
      </div>

      <BillingUsersTable
        :all-users-selected="allUsersSelected"
        :batch-amount="batchGrantForm.amount"
        :batch-granting="batchGranting"
        :batch-reason="batchGrantForm.reason"
        :assigning-plan="assigningPlan"
        :assigning-plan-user-id="assigningPlanUserId"
        :identity-conflict-count="identityConflictCount"
        :loading="loadingUsers"
        :payment-check-disabled="paymentCheckProviderOptions.length === 0"
        :payment-record-backfill-disabled="
          paymentRecordBackfillProviderOptions.length === 0
        "
        :selected-user-id="selectedUserId"
        :selected-user-ids="selectedUserIds"
        :search="userSearch"
        :user-count="userCount"
        :user-page-overflow="userPageOverflow"
        :users="users"
        @batch-grant="batchGrantCredits"
        @clear-selection="clearSelectedUsers"
        @assign-plan="openAssignPlan"
        @grant-user="openGrantUser"
        @open-user="openUser"
        @show-identity-conflicts="openIdentityConflictDialog"
        @payment-record-backfill="openPaymentRecordBackfillDialog"
        @payment-check="openPaymentCheckDialog"
        @refresh="loadUsers"
        @toggle-all="toggleAllUsers"
        @toggle-user="toggleUserSelection"
        @update:batchAmount="batchGrantForm.amount = $event"
        @update:batchReason="batchGrantForm.reason = $event"
        @update:search="userSearch = $event"
      />

      <BillingUserDrawer
        :detail-loading="detailLoading"
        :detail-payments="detailPayments"
        :detail-subscriptions="detailSubscriptions"
        :detail-transactions="detailTransactions"
        :open="drawerOpen"
        :selected-detail-tab="selectedDetailTab"
        :selected-user="selectedUser"
        @close="closeDrawer"
        @update:selectedDetailTab="selectedDetailTab = $event"
      />

      <transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="identityConflictModalOpen"
          class="fixed inset-0 z-50 bg-gray-900/50"
          aria-hidden="true"
          @click="closeIdentityConflictDialog"
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
          v-if="identityConflictModalOpen"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <section
            class="w-full max-w-3xl rounded-2xl border border-gray-200 bg-white shadow-2xl"
            role="dialog"
            :aria-label="t('billing.users.identityConflictDialogTitle')"
          >
            <div
              class="flex items-center justify-between border-b border-gray-200 px-6 py-5"
            >
              <div>
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.users.identityConflictDialogTitle') }}
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                  {{ t('billing.users.identityConflictDialogHint') }}
                </p>
              </div>
              <button
                type="button"
                class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                :aria-label="t('common.close')"
                @click="closeIdentityConflictDialog"
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

            <div class="space-y-4 p-6">
              <div
                v-if="identityConflictUsers.length === 0"
                class="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
              >
                {{ t('billing.users.identityConflictEmpty') }}
              </div>
              <div v-else class="space-y-3">
                <article
                  v-for="item in identityConflictUsers"
                  :key="item.user_id"
                  class="rounded-xl border border-amber-200 bg-amber-50/60 p-4"
                >
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-gray-900">
                        #{{ item.user_id }} {{ item.username }}
                      </p>
                      <p class="mt-1 text-xs text-gray-600">
                        {{ item.email || '—' }}
                      </p>
                    </div>
                    <span
                      class="inline-flex rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700"
                    >
                      {{ t('billing.users.identityConflictChip') }}
                    </span>
                  </div>
                  <div class="mt-3 space-y-2">
                    <div
                      v-for="customer in item.identity_conflict_customers || []"
                      :key="customer.id"
                      class="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm text-gray-700"
                    >
                      <div
                        class="flex flex-wrap items-center justify-between gap-2"
                      >
                        <span class="font-medium text-gray-900">
                          {{ customer.id }}
                        </span>
                        <span class="text-xs text-gray-500">
                          {{ customer.subscriber_username || '—' }}
                        </span>
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        {{
                          customer.match_sources &&
                          customer.match_sources.length > 0
                            ? customer.match_sources.join(' · ')
                            : '—'
                        }}
                      </p>
                    </div>
                  </div>
                </article>
              </div>

              <div class="flex items-center justify-end">
                <BaseButton
                  variant="outline"
                  size="sm"
                  @click="closeIdentityConflictDialog"
                >
                  {{ t('common.close') }}
                </BaseButton>
              </div>
            </div>
          </section>
        </div>
      </transition>

      <BillingUserGrantPanel
        :grant-amount="grantForm.amount"
        :grant-reason="grantForm.reason"
        :granting="granting"
        :open="grantModalOpen"
        :selected-user="selectedGrantUser"
        @close="closeGrantModal"
        @grant-credits="grantCredits"
        @update:grantAmount="grantForm.amount = $event"
        @update:grantReason="grantForm.reason = $event"
      />

      <BillingUserPlanPanel
        :open="planModalOpen"
        :plans="plans"
        :selected-plan-id="selectedPlanId"
        :selected-user="selectedPlanUser"
        :switching="switchingPlan"
        @close="closePlanModal"
        @switch-plan="switchPlan"
        @update:selectedPlanId="selectedPlanId = $event"
      />

      <BillingPaymentCheckDialog
        :open="paymentCheckModalOpen"
        :result="paymentCheckLastResult"
        :provider-options="paymentCheckProviderOptions"
        :running="paymentCheckRunning"
        :syncing-user-id="paymentCheckSyncingUserId"
        :selected-providers="paymentCheckSelectedProviders"
        @close="closePaymentCheckDialog"
        @run="runPaymentCheck"
        @sync-user="syncPaymentCheckUser"
        @update:selectedProviders="paymentCheckSelectedProviders = $event"
      />

      <transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="paymentRecordBackfillModalOpen"
          class="fixed inset-0 z-50 bg-gray-900/50"
          aria-hidden="true"
          @click="closePaymentRecordBackfillDialog"
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
          v-if="paymentRecordBackfillModalOpen"
          class="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <section
            class="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white shadow-2xl"
            role="dialog"
            :aria-label="t('billing.sections.paymentRecordBackfill')"
          >
            <div
              class="flex items-center justify-between border-b border-gray-200 px-6 py-5"
            >
              <div>
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('billing.sections.paymentRecordBackfill') }}
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                  {{ t('billing.config.paymentRecordBackfillRunNowHint') }}
                </p>
              </div>
              <button
                type="button"
                class="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                :aria-label="t('common.close')"
                @click="closePaymentRecordBackfillDialog"
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
              <section class="space-y-3">
                <div>
                  <p class="text-sm font-medium text-gray-900">
                    {{ t('billing.config.paymentRecordBackfillProviders') }}
                  </p>
                  <p class="mt-1 text-xs text-gray-500">
                    {{ t('billing.config.paymentRecordBackfillProvidersHint') }}
                  </p>
                </div>
                <div
                  v-if="paymentRecordBackfillProviderOptions.length > 0"
                  class="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4"
                >
                  <label
                    v-for="provider in paymentRecordBackfillProviderOptions"
                    :key="provider.value"
                    class="flex items-start gap-3 rounded-md border border-gray-200 bg-white px-3 py-2"
                  >
                    <input
                      v-model="paymentRecordBackfillSelectedProviders"
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
                </div>
                <div
                  v-else
                  class="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center text-sm text-gray-500"
                >
                  {{ t('billing.config.noProviders') }}
                </div>
              </section>

              <div class="flex items-center justify-end gap-3">
                <BaseButton
                  variant="outline"
                  size="sm"
                  @click="closePaymentRecordBackfillDialog"
                >
                  {{ t('common.close') }}
                </BaseButton>
                <BaseButton
                  variant="primary"
                  size="sm"
                  :loading="paymentRecordBackfillRunning"
                  :disabled="paymentRecordBackfillRunning"
                  @click="runPaymentRecordBackfill"
                >
                  {{ t('billing.config.paymentRecordBackfillRunNow') }}
                </BaseButton>
              </div>
            </div>
          </section>
        </div>
      </transition>
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
import BillingUsersTable from './components/BillingUsersTable.vue'
import BillingUserGrantPanel from './components/BillingUserGrantPanel.vue'
import BillingUserDrawer from './components/BillingUserDrawer.vue'
import BillingUserPlanPanel from './components/BillingUserPlanPanel.vue'
import BillingPaymentCheckDialog from './components/BillingPaymentCheckDialog.vue'
import { isStripeProvider } from './utils/provider'

const { t } = useI18n()
const toast = useToast()

const loadingUsers = ref(true)
const granting = ref(false)
const switchingPlan = ref(false)
const assigningPlan = ref(false)
const assigningPlanUserId = ref(null)
const batchGranting = ref(false)
const paymentCheckRunning = ref(false)
const paymentCheckSyncingUserId = ref(null)
const paymentCheckModalOpen = ref(false)
const paymentCheckSelectedProviders = ref(['stripe'])
const paymentCheckLastResult = ref(null)
const paymentRecordBackfillModalOpen = ref(false)
const paymentRecordBackfillRunning = ref(false)
const paymentRecordBackfillError = ref('')
const paymentRecordBackfillSuccess = ref('')
const paymentRecordBackfillSelectedProviders = ref(['stripe'])
const identityConflictModalOpen = ref(false)
const identityConflictCount = ref(0)
const identityConflictUsers = ref([])
const billingConfig = ref(null)
const configLoading = ref(false)
const userCount = ref(0)
const userPageOverflow = ref(false)

const users = ref([])
const plans = ref([])
const selectedUserId = ref(null)
const selectedGrantUserId = ref(null)
const selectedPlanUserId = ref(null)
const selectedPlanId = ref(null)
const selectedUserIds = ref([])
const drawerOpen = ref(false)
const grantModalOpen = ref(false)
const planModalOpen = ref(false)
const selectedDetailTab = ref('overview')

const detailLoading = ref(false)
const detailTransactions = ref([])
const detailPayments = ref([])
const detailSubscriptions = ref([])

const userSearch = ref('')
const grantForm = reactive({
  amount: 10,
  reason: 'manual_top_up'
})

const batchGrantForm = reactive({
  amount: 10,
  reason: 'manual_top_up'
})

const selectedUser = computed(() => {
  return (
    users.value.find((item) => item.user_id === selectedUserId.value) || null
  )
})

const selectedGrantUser = computed(() => {
  return (
    users.value.find((item) => item.user_id === selectedGrantUserId.value) ||
    null
  )
})

const selectedPlanUser = computed(() => {
  return (
    users.value.find((item) => item.user_id === selectedPlanUserId.value) ||
    null
  )
})

const paymentCheckProviderOptions = computed(() => {
  const configuredProviders = Array.isArray(
    billingConfig.value?.payment_check_providers
  )
    ? billingConfig.value.payment_check_providers.filter(
        (provider) =>
          String(provider || '')
            .trim()
            .toLowerCase() !== 'platform'
      )
    : []
  const providers =
    configuredProviders.length > 0 ? configuredProviders : ['stripe']

  return providers.map((provider) => ({
    value: provider,
    label: formatProviderLabel(provider)
  }))
})

const paymentRecordBackfillProviderOptions = computed(
  () => paymentCheckProviderOptions.value
)

const allUsersSelected = computed(() => {
  return (
    users.value.length > 0 &&
    users.value.every((item) => selectedUserIds.value.includes(item.user_id))
  )
})

async function loadUsers() {
  loadingUsers.value = true
  try {
    const data = await billingAdminApi.getUsers({
      search: userSearch.value.trim() || undefined,
      page_size: 100
    })
    users.value = data.results || []
    userCount.value = data.count || users.value.length
    userPageOverflow.value = userCount.value > users.value.length
    selectedUserIds.value = selectedUserIds.value.filter((userId) =>
      users.value.some((item) => item.user_id === userId)
    )
    if (selectedGrantUserId.value) {
      const stillGrantTarget = users.value.find(
        (item) => item.user_id === selectedGrantUserId.value
      )
      if (!stillGrantTarget) {
        selectedGrantUserId.value = null
        grantModalOpen.value = false
      }
    }
    if (selectedUserId.value) {
      const stillSelected = users.value.find(
        (item) => item.user_id === selectedUserId.value
      )
      if (!stillSelected) {
        selectedUserId.value = null
        drawerOpen.value = false
      }
    }
    if (identityConflictModalOpen.value && identityConflictCount.value === 0) {
      identityConflictModalOpen.value = false
    }
    await loadIdentityConflicts()
  } catch (error) {
    console.error('Failed to load billing users:', error)
    users.value = []
    identityConflictCount.value = 0
    identityConflictUsers.value = []
    userCount.value = 0
    userPageOverflow.value = false
    identityConflictModalOpen.value = false
  } finally {
    loadingUsers.value = false
  }
}

async function loadIdentityConflicts() {
  try {
    const data = await billingAdminApi.getIdentityConflicts()
    identityConflictCount.value = data.count || 0
    identityConflictUsers.value = data.results || []
    if (identityConflictModalOpen.value && identityConflictCount.value === 0) {
      identityConflictModalOpen.value = false
    }
  } catch (error) {
    console.error('Failed to load billing identity conflicts:', error)
    identityConflictCount.value = 0
    identityConflictUsers.value = []
    identityConflictModalOpen.value = false
  }
}

async function loadPlans() {
  try {
    plans.value = await billingAdminApi.getPlans()
  } catch (error) {
    console.error('Failed to load billing plans:', error)
    plans.value = []
  }
}

async function loadConfig() {
  configLoading.value = true
  try {
    billingConfig.value = await billingAdminApi.getConfig()
    const backfillProviders = Array.isArray(
      billingConfig.value?.payment_record_backfill_providers
    )
      ? billingConfig.value.payment_record_backfill_providers.filter(
          (provider) =>
            String(provider || '')
              .trim()
              .toLowerCase() !== 'platform'
        )
      : []
    paymentRecordBackfillSelectedProviders.value =
      backfillProviders.length > 0
        ? backfillProviders
        : paymentRecordBackfillProviderOptions.value.map((item) => item.value)
  } catch (error) {
    console.error('Failed to load billing config:', error)
    billingConfig.value = null
  } finally {
    configLoading.value = false
  }
}

function clearSelectedUsers() {
  selectedUserIds.value = []
}

function toggleUserSelection(userId) {
  if (selectedUserIds.value.includes(userId)) {
    selectedUserIds.value = selectedUserIds.value.filter(
      (item) => item !== userId
    )
    return
  }
  selectedUserIds.value = [...selectedUserIds.value, userId]
}

function toggleAllUsers() {
  if (allUsersSelected.value) {
    clearSelectedUsers()
    return
  }
  selectedUserIds.value = users.value.map((item) => item.user_id)
}

async function loadSelectedUserDetail(userId) {
  detailLoading.value = true
  try {
    const [transactionsRes, paymentsRes, subscriptionsRes] =
      await Promise.allSettled([
        billingAdminApi.getTransactions({
          user_id: userId,
          page_size: 20
        }),
        billingAdminApi.getPayments({
          user_id: userId,
          page_size: 20
        }),
        billingAdminApi.getSubscriptions({
          user_id: userId,
          page_size: 20
        })
      ])

    detailTransactions.value =
      transactionsRes.status === 'fulfilled'
        ? transactionsRes.value.results || []
        : []
    detailPayments.value =
      paymentsRes.status === 'fulfilled' ? paymentsRes.value.results || [] : []
    detailSubscriptions.value =
      subscriptionsRes.status === 'fulfilled'
        ? subscriptionsRes.value.results || []
        : []
  } catch (error) {
    console.error('Failed to load user billing detail:', error)
    detailTransactions.value = []
    detailPayments.value = []
    detailSubscriptions.value = []
  } finally {
    detailLoading.value = false
  }
}

function openUser(row) {
  selectedUserId.value = row.user_id
  drawerOpen.value = true
  selectedDetailTab.value = 'overview'
  loadSelectedUserDetail(row.user_id)
}

function openGrantUser(row) {
  selectedGrantUserId.value = row.user_id
  grantForm.amount = 10
  grantForm.reason = 'manual_top_up'
  grantModalOpen.value = true
}

function openAssignPlan(row) {
  if (!row?.user_id) {
    toast.showWarning(t('billing.users.assignPlanInvalid'))
    return
  }
  if (isStripeProvider(row.provider_key, row.provider_name)) {
    toast.showWarning(t('billing.users.assignPlanBlockedStripe'))
    return
  }
  selectedPlanUserId.value = row.user_id
  selectedPlanId.value =
    row.plan_id || plans.value.find((plan) => plan.slug === 'free')?.id || null
  planModalOpen.value = true
}

function openPaymentCheckDialog() {
  paymentCheckSelectedProviders.value = paymentCheckProviderOptions.value.map(
    (item) => item.value
  )
  paymentCheckLastResult.value = null
  paymentCheckModalOpen.value = true
}

function closePaymentCheckDialog() {
  paymentCheckModalOpen.value = false
}

function openPaymentRecordBackfillDialog() {
  paymentRecordBackfillSelectedProviders.value =
    paymentRecordBackfillProviderOptions.value.map((item) => item.value)
  paymentRecordBackfillModalOpen.value = true
}

function closePaymentRecordBackfillDialog() {
  paymentRecordBackfillModalOpen.value = false
}

function openIdentityConflictDialog() {
  if (identityConflictCount.value === 0) {
    return
  }
  identityConflictModalOpen.value = true
}

function closeIdentityConflictDialog() {
  identityConflictModalOpen.value = false
}

function formatProviderLabel(provider) {
  const normalized = String(provider || '')
    .trim()
    .toLowerCase()
  if (normalized === 'stripe') return t('billing.paymentCheck.providerStripe')
  if (normalized === 'platform') {
    return t('billing.paymentCheck.providerPlatform')
  }
  return provider
}

function removePaymentCheckUserFromResult(userId) {
  if (!paymentCheckLastResult.value) return

  const nextResult = { ...paymentCheckLastResult.value }
  const sourceGroups = Array.isArray(nextResult.provider_runs)
    ? nextResult.provider_runs
    : Array.isArray(nextResult.providers)
      ? nextResult.providers
      : []

  const filteredGroups = sourceGroups.map((group) => {
    const differences = Array.isArray(group.differences)
      ? group.differences.filter(
          (difference) => Number(difference.user_id) !== Number(userId)
        )
      : []
    return {
      ...group,
      differences
    }
  })

  if (Array.isArray(nextResult.provider_runs)) {
    nextResult.provider_runs = filteredGroups
  }
  if (Array.isArray(nextResult.providers)) {
    nextResult.providers = filteredGroups
  }

  paymentCheckLastResult.value = nextResult
}

async function runPaymentCheck() {
  if (paymentCheckSelectedProviders.value.length === 0) {
    toast.showWarning(t('billing.paymentCheck.noProvidersSelected'))
    return
  }
  paymentCheckRunning.value = true
  try {
    const result = await billingAdminApi.runPaymentCheck({
      providers: paymentCheckSelectedProviders.value
    })
    paymentCheckLastResult.value = result
    toast.showSuccess(
      t('billing.paymentCheck.runSuccess', {
        repaired: result?.totals?.repaired_count || 0,
        manual: result?.totals?.manual_count || 0,
        scanned: result?.totals?.scanned_count || 0
      })
    )
    await loadUsers()
    if (drawerOpen.value && selectedUserId.value) {
      await loadSelectedUserDetail(selectedUserId.value)
    }
  } catch (error) {
    console.error('Failed to run payment check:', error)
    toast.showError(t('billing.paymentCheck.runFailed'))
  } finally {
    paymentCheckRunning.value = false
  }
}

async function runPaymentRecordBackfill() {
  if (paymentRecordBackfillSelectedProviders.value.length === 0) {
    toast.showWarning(t('billing.paymentCheck.noProvidersSelected'))
    return
  }
  paymentRecordBackfillRunning.value = true
  paymentRecordBackfillError.value = ''
  paymentRecordBackfillSuccess.value = ''
  try {
    const result = await billingAdminApi.runPaymentRecordBackfill({
      providers: paymentRecordBackfillSelectedProviders.value
    })
    const summary = [
      `${t('billing.config.paymentRecordBackfillCreated')}: ${
        result?.created ?? 0
      }`,
      `${t('billing.config.paymentRecordBackfillUpdated')}: ${
        result?.updated ?? 0
      }`,
      `${t('billing.config.paymentRecordBackfillSkipped')}: ${
        result?.skipped ?? 0
      }`
    ].join(' · ')
    paymentRecordBackfillSuccess.value = summary
    toast.showSuccess(summary)
    paymentRecordBackfillModalOpen.value = false
    await loadUsers()
    if (drawerOpen.value && selectedUserId.value) {
      await loadSelectedUserDetail(selectedUserId.value)
    }
  } catch (error) {
    console.error('Failed to backfill payment records:', error)
    paymentRecordBackfillError.value = t(
      'billing.config.paymentRecordBackfillRunFailed'
    )
    toast.showError(paymentRecordBackfillError.value)
  } finally {
    paymentRecordBackfillRunning.value = false
  }
}

async function syncPaymentCheckUser(userId) {
  if (!userId) return
  paymentCheckSyncingUserId.value = userId
  try {
    await billingAdminApi.syncUserFromStripe(userId)
    toast.showSuccess(t('billing.users.syncStripeSuccess'))
    removePaymentCheckUserFromResult(userId)
    await loadUsers()
    if (drawerOpen.value && selectedUserId.value) {
      await loadSelectedUserDetail(selectedUserId.value)
    }
    const result = await billingAdminApi.runPaymentCheck({
      providers: paymentCheckSelectedProviders.value
    })
    paymentCheckLastResult.value = result
  } catch (error) {
    console.error('Failed to sync payment check user from Stripe:', error)
    toast.showError(t('billing.users.syncStripeFailed'))
  } finally {
    paymentCheckSyncingUserId.value = null
  }
}

function closePlanModal() {
  planModalOpen.value = false
}

async function switchPlan() {
  if (!selectedPlanUser.value) {
    toast.showWarning(t('billing.users.assignPlanInvalid'))
    return
  }
  if (!selectedPlanId.value) {
    toast.showWarning(t('billing.users.targetPlanPlaceholder'))
    return
  }
  switchingPlan.value = true
  assigningPlan.value = true
  assigningPlanUserId.value = selectedPlanUser.value.user_id
  try {
    await billingAdminApi.assignPlan(selectedPlanUser.value.user_id, {
      plan_id: Number(selectedPlanId.value)
    })
    toast.showSuccess(t('billing.users.assignPlanSuccess'))
    await loadUsers()
    if (selectedUserId.value === selectedPlanUser.value.user_id) {
      await loadSelectedUserDetail(selectedPlanUser.value.user_id)
    }
    planModalOpen.value = false
  } catch (error) {
    console.error('Failed to assign plan:', error)
    toast.showError(t('billing.users.assignPlanFailed'))
  } finally {
    switchingPlan.value = false
    assigningPlan.value = false
    assigningPlanUserId.value = null
  }
}

function closeDrawer() {
  drawerOpen.value = false
}

function closeGrantModal() {
  grantModalOpen.value = false
}

async function grantCredits() {
  if (!selectedGrantUser.value) {
    toast.showWarning(t('billing.users.selectGrantUserFirst'))
    return
  }
  if (!grantForm.amount) {
    toast.showWarning(t('billing.users.grantInvalid'))
    return
  }
  granting.value = true
  try {
    const data = await billingAdminApi.grantCredits(
      selectedGrantUser.value.user_id,
      {
        amount: Number(grantForm.amount),
        reason: grantForm.reason || 'manual_top_up'
      }
    )
    const nextCredits = data?.credits
    if (nextCredits) {
      const index = users.value.findIndex(
        (item) => item.user_id === selectedGrantUser.value.user_id
      )
      if (index >= 0) {
        users.value[index] = {
          ...users.value[index],
          ...nextCredits,
          user_id: selectedGrantUser.value.user_id
        }
      }
    }
    toast.showSuccess(t('billing.users.grantSuccess'))
    await loadUsers()
    if (selectedUser.value) {
      await loadSelectedUserDetail(selectedUser.value.user_id)
    }
    grantModalOpen.value = false
  } catch (error) {
    console.error('Failed to grant credits:', error)
    toast.showError(t('billing.users.grantFailed'))
  } finally {
    granting.value = false
  }
}

async function batchGrantCredits() {
  if (selectedUserIds.value.length === 0 || !batchGrantForm.amount) {
    toast.showWarning(t('billing.users.batchGrantInvalid'))
    return
  }
  batchGranting.value = true
  try {
    await billingAdminApi.batchGrantCredits({
      user_ids: selectedUserIds.value,
      amount: Number(batchGrantForm.amount),
      reason: batchGrantForm.reason || 'manual_top_up'
    })
    toast.showSuccess(t('billing.users.batchGrantSuccess'))
    clearSelectedUsers()
    await loadUsers()
    if (drawerOpen.value && selectedUserId.value) {
      await loadSelectedUserDetail(selectedUserId.value)
    }
  } catch (error) {
    console.error('Failed to batch grant credits:', error)
    toast.showError(t('billing.users.batchGrantFailed'))
  } finally {
    batchGranting.value = false
  }
}

onMounted(() => {
  loadConfig()
  loadPlans()
  loadUsers()
})
</script>
