<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('billing.usersPageTitle') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('billing.usersPageSubtitle') }}
        </p>
      </div>

      <BillingUsersTable
        :all-users-selected="allUsersSelected"
        :batch-amount="batchGrantForm.amount"
        :batch-granting="batchGranting"
        :batch-reason="batchGrantForm.reason"
        :loading="loadingUsers"
        :selected-user-id="selectedUserId"
        :selected-user-ids="selectedUserIds"
        :search="userSearch"
        :user-count="userCount"
        :user-page-overflow="userPageOverflow"
        :users="users"
        @batch-grant="batchGrantCredits"
        @clear-selection="clearSelectedUsers"
        @grant-user="openGrantUser"
        @open-user="openUser"
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
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import { billingAdminApi } from '@/admin/api'
import BillingUsersTable from './components/BillingUsersTable.vue'
import BillingUserGrantPanel from './components/BillingUserGrantPanel.vue'
import BillingUserDrawer from './components/BillingUserDrawer.vue'

const { t } = useI18n()
const toast = useToast()

const loadingUsers = ref(true)
const granting = ref(false)
const batchGranting = ref(false)
const userCount = ref(0)
const userPageOverflow = ref(false)

const users = ref([])
const selectedUserId = ref(null)
const selectedGrantUserId = ref(null)
const selectedUserIds = ref([])
const drawerOpen = ref(false)
const grantModalOpen = ref(false)
const selectedDetailTab = ref('transactions')

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
  } catch (error) {
    console.error('Failed to load billing users:', error)
    users.value = []
    userCount.value = 0
    userPageOverflow.value = false
  } finally {
    loadingUsers.value = false
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
  selectedDetailTab.value = 'transactions'
  loadSelectedUserDetail(row.user_id)
}

function openGrantUser(row) {
  selectedGrantUserId.value = row.user_id
  grantForm.amount = 10
  grantForm.reason = 'manual_top_up'
  grantModalOpen.value = true
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
  loadUsers()
})
</script>
