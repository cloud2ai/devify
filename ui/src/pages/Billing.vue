<template>
  <AppLayout>
    <div class="space-y-4">
      <div>
        <h2 class="text-lg font-bold leading-7 text-gray-900 sm:text-xl">
          {{ t('billing.title') }}
        </h2>
        <p class="mt-0.5 text-xs text-gray-500">
          {{ t('billing.description') }}
        </p>
      </div>

      <div
        v-if="successMessage"
        class="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between"
      >
        <div class="flex items-center">
          <svg
            class="w-5 h-5 text-green-600 mr-3"
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
          <span class="text-green-800">{{ successMessage }}</span>
        </div>
        <button
          @click="successMessage = ''"
          class="text-green-600 hover:text-green-800"
        >
          <svg
            class="w-5 h-5"
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

      <div
        v-if="errorMessage"
        class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between"
      >
        <div class="flex items-center">
          <svg
            class="w-5 h-5 text-red-600 mr-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span class="text-red-800">{{ errorMessage }}</span>
        </div>
        <button
          @click="errorMessage = ''"
          class="text-red-600 hover:text-red-800"
        >
          <svg
            class="w-5 h-5"
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

      <div v-if="loading" class="flex items-center justify-center py-12">
        <div
          class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
        ></div>
        <p class="ml-3 text-sm text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div class="lg:col-span-1">
            <CurrentSubscription
              :subscription="currentSubscription"
              :credits="credits"
            />
          </div>

          <div class="lg:col-span-2">
            <SubscriptionPlans
              :current-subscription="currentSubscription"
              @subscription-updated="handleSubscriptionUpdated"
              @operation-success="handleOperationSuccess"
              @operation-error="handleOperationError"
            />
          </div>
        </div>

        <UsageChart />

        <CreditUsageList />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '@/components/layout/AppLayout.vue'
import CurrentSubscription from '@/components/billing/CurrentSubscription.vue'
import SubscriptionPlans from '@/components/billing/SubscriptionPlans.vue'
import UsageChart from '@/components/billing/UsageChart.vue'
import CreditUsageList from '@/components/billing/CreditUsageList.vue'
import billingApi from '@/api/billing'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const currentSubscription = ref(null)
const credits = ref(null)
const successMessage = ref('')
const errorMessage = ref('')

async function fetchData() {
  loading.value = true

  try {
    const [subscriptionRes, creditsRes] = await Promise.allSettled([
      billingApi.getCurrentSubscription(),
      billingApi.getUserCredits()
    ])

    if (subscriptionRes.status === 'fulfilled') {
      const subscriptionData =
        subscriptionRes.value.data?.data ?? subscriptionRes.value.data ?? null
      currentSubscription.value = subscriptionData
    }

    if (creditsRes.status === 'fulfilled') {
      const creditsData = creditsRes.value.data?.data ?? creditsRes.value.data
      credits.value = creditsData
    }
  } catch (error) {
    console.error('Failed to fetch billing data:', error)
    errorMessage.value = t('billing.errors.fetchFailed')
  } finally {
    loading.value = false
  }
}

function handleSubscriptionUpdated() {
  fetchData()
}

function handleOperationSuccess(operationType) {
  if (operationType === 'cancel') {
    successMessage.value = t('billing.messages.cancelSuccess')
  } else if (operationType === 'downgrade') {
    successMessage.value = t('billing.messages.downgradeSuccess')
  } else if (operationType === 'resume') {
    successMessage.value = t('billing.messages.resumeSuccess')
  }

  setTimeout(() => {
    successMessage.value = ''
  }, 5000)
}

function handleOperationError(errorMsg) {
  errorMessage.value = errorMsg

  setTimeout(() => {
    errorMessage.value = ''
  }, 5000)
}

function handleStripeCallback() {
  const success = route.query.success
  const canceled = route.query.canceled

  if (success === 'true') {
    successMessage.value = t('billing.messages.paymentSuccess')

    router.replace({ query: {} })

    setTimeout(() => {
      fetchData()
    }, 2000)
  } else if (canceled === 'true') {
    errorMessage.value = t('billing.messages.paymentCanceled')

    router.replace({ query: {} })
  }
}

onMounted(() => {
  handleStripeCallback()
  fetchData()
})
</script>
