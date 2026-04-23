<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
    <div class="mb-4">
      <h3 class="text-base font-semibold text-gray-900 mb-3">
        {{ t('billing.usageStats.title') }}
      </h3>

      <div
        class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between"
      >
        <div class="flex gap-2">
          <button
            v-for="period in periods"
            :key="period.value"
            @click="selectPeriod(period.value)"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-md transition-colors',
              selectedPeriod === period.value
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            ]"
          >
            {{ period.label }}
          </button>
        </div>

        <div class="flex items-center gap-2">
          <input
            v-model="customStartDate"
            type="date"
            class="px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            @change="handleCustomDateChange"
          />
          <span class="text-gray-500">-</span>
          <input
            v-model="customEndDate"
            type="date"
            class="px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            @change="handleCustomDateChange"
          />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
      <div class="bg-gray-50 rounded-lg p-3">
        <div class="text-xs text-gray-500 mb-0.5">
          {{ t('billing.usageStats.totalConsumed') }}
        </div>
        <div class="text-xl font-semibold text-gray-900">
          {{ stats?.total_consumed || 0 }}
        </div>
      </div>

      <div class="bg-gray-50 rounded-lg p-3">
        <div class="text-xs text-gray-500 mb-0.5">
          {{ t('billing.usageStats.available') }}
        </div>
        <div class="text-xl font-semibold text-primary-600">
          {{ stats?.total_available || 0 }}
        </div>
      </div>

      <div class="bg-gray-50 rounded-lg p-3">
        <div class="text-xs text-gray-500 mb-0.5">
          {{ t('billing.usageStats.totalCredits') }}
        </div>
        <div class="text-xl font-semibold text-gray-900">
          {{ stats?.total_credits || 0 }}
        </div>
      </div>
    </div>

    <div class="relative" style="height: 240px">
      <Line
        v-if="!loading && chartData"
        :data="chartData"
        :options="chartOptions"
      />
      <div v-else-if="loading" class="flex items-center justify-center h-full">
        <div class="text-gray-500">{{ t('common.loading') }}</div>
      </div>
      <div v-else class="flex items-center justify-center h-full">
        <div class="text-gray-500">{{ t('common.noData') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import billingApi from '@/api/billing'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const { t } = useI18n()

const loading = ref(false)
const stats = ref(null)
const selectedPeriod = ref(30)
const customStartDate = ref('')
const customEndDate = ref('')

const periods = [
  { value: 1, label: '1d' },
  { value: 7, label: '7d' },
  { value: 30, label: '30d' }
]

const chartData = computed(() => {
  if (!stats.value || !stats.value.stats) {
    return null
  }

  const dates = stats.value.stats.map((item) => {
    const date = new Date(item.date)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  })

  const consumed = stats.value.stats.map((item) => item.consumed)

  return {
    labels: dates,
    datasets: [
      {
        label: t('billing.usageStats.creditsConsumed'),
        data: consumed,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.3,
        fill: true
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      callbacks: {
        label: function (context) {
          return `${context.dataset.label}: ${context.parsed.y} credits`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        precision: 0
      }
    },
    x: {
      grid: {
        display: false
      }
    }
  }
}

async function fetchUsageStats(startDate = null, endDate = null) {
  loading.value = true
  try {
    const response = await billingApi.getUsageStats(startDate, endDate)
    const statsData = response.data.data || response.data
    stats.value = statsData
  } catch (error) {
    console.error('Failed to fetch usage stats:', error)
  } finally {
    loading.value = false
  }
}

function selectPeriod(days) {
  selectedPeriod.value = days
  customStartDate.value = ''
  customEndDate.value = ''

  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)

  fetchUsageStats(startDate.toISOString(), endDate.toISOString())
}

function handleCustomDateChange() {
  if (customStartDate.value && customEndDate.value) {
    selectedPeriod.value = null

    const startDate = new Date(customStartDate.value)
    const endDate = new Date(customEndDate.value)

    fetchUsageStats(startDate.toISOString(), endDate.toISOString())
  }
}

onMounted(() => {
  selectPeriod(30)
})
</script>
