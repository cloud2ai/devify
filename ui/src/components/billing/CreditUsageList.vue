<template>
  <BaseCard>
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <svg
            class="w-5 h-5 text-gray-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <h3 class="text-base font-semibold text-gray-800">
            {{ t('billing.creditUsage.title') }}
          </h3>
        </div>
        <!-- Time range filter -->
        <select
          v-model="selectedRange"
          @change="fetchUsageList"
          class="text-xs border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="7">{{ t('billing.creditUsage.last7Days') }}</option>
          <option value="30">{{ t('billing.creditUsage.last30Days') }}</option>
          <option value="90">{{ t('billing.creditUsage.last90Days') }}</option>
        </select>
      </div>
    </template>

    <div v-if="loading" class="flex items-center justify-center py-8">
      <div
        class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"
      ></div>
      <p class="ml-3 text-sm text-gray-500">{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="usageList.length === 0" class="text-center py-8">
      <svg
        class="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
        />
      </svg>
      <p class="mt-2 text-sm text-gray-500">
        {{ t('billing.creditUsage.noData') }}
      </p>
    </div>

    <div v-else class="divide-y divide-gray-200">
      <!-- List item -->
      <div
        v-for="item in usageList"
        :key="item.id"
        class="flex items-center justify-between py-3 hover:bg-gray-50 transition-colors cursor-pointer"
        @click="goToChat(item.chat_id)"
      >
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <!-- Icon -->
          <div class="flex-shrink-0">
            <div
              class="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center"
            >
              <svg
                class="w-5 h-5 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
          </div>

          <!-- Chat info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <p class="text-sm font-medium text-gray-900 truncate">
                {{ item.subject || t('billing.creditUsage.noSubject') }}
              </p>
              <!-- Status badge -->
              <StatusBadge v-if="item.status" :status="item.status" />
            </div>
            <p class="text-xs text-gray-500">
              {{ formatRelativeDate(item.created_at, t) }}
            </p>
          </div>

          <!-- Credit amount -->
          <div class="flex-shrink-0 text-right">
            <span
              class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700"
            >
              -{{ item.amount }}
              <svg
                class="ml-1 w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="totalPages > 1"
      class="flex items-center justify-between border-t border-gray-200 pt-3 mt-3"
    >
      <button
        @click="prevPage"
        :disabled="currentPage === 1"
        class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
      >
        <svg
          class="w-4 h-4 mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
        {{ t('common.previous') }}
      </button>

      <span class="text-xs text-gray-600">
        {{ t('common.pageInfo', { current: currentPage, total: totalPages }) }}
      </span>

      <button
        @click="nextPage"
        :disabled="currentPage === totalPages"
        class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
      >
        {{ t('common.next') }}
        <svg
          class="w-4 h-4 ml-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>
    </div>
  </BaseCard>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import billingApi from '@/api/billing'
import { formatRelativeDate } from '@/utils/timezone'
import BaseCard from '@/components/ui/BaseCard.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const usageList = ref([])
const selectedRange = ref('30')
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 10

const fetchUsageList = async () => {
  loading.value = true
  try {
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - parseInt(selectedRange.value))

    const response = await billingApi.getCreditUsageList({
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      page: currentPage.value,
      page_size: pageSize
    })

    const responseData = response.data.data || response.data
    usageList.value = responseData.results || []
    totalPages.value = Math.ceil((responseData.count || 0) / pageSize)
  } catch (error) {
    console.error('Failed to fetch credit usage list:', error)
    usageList.value = []
  } finally {
    loading.value = false
  }
}

const goToChat = (chatId) => {
  if (chatId) {
    router.push(`/chats/${chatId}`)
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchUsageList()
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    fetchUsageList()
  }
}

onMounted(() => {
  fetchUsageList()
})
</script>
