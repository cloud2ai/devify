<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('notificationManagement.stats.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('notificationManagement.stats.subtitle') }}
        </p>
      </div>

      <section
        class="w-full bg-white rounded-2xl border border-gray-200 shadow-sm p-4 sm:p-5 flex flex-wrap items-end justify-between gap-6 mb-6"
        aria-label="Filters"
      >
        <div class="flex flex-wrap items-end gap-6 flex-1 min-w-0">
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{ t('notificationManagement.stats.userScope') }}
            </label>
            <select
              v-model="userScope"
              class="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 min-w-[140px] hover:border-gray-300 transition-colors"
              @change="fetchStats"
            >
              <option value="">
                {{ t('notificationManagement.stats.allUsers') }}
              </option>
              <option
                v-for="u in userOptions"
                :key="u.user_id"
                :value="String(u.user_id)"
              >
                {{ u.display }}
              </option>
            </select>
          </div>
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{ t('notificationManagement.stats.granularity') }}
            </label>
            <div class="flex rounded-lg bg-gray-100 p-1">
              <button
                v-for="opt in granularityOptions"
                :key="opt.value"
                type="button"
                :class="[
                  'px-4 py-1.5 text-xs font-semibold rounded-md transition-colors',
                  granularity === opt.value
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                ]"
                @click="selectGranularity(opt.value)"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{
                granularity === 'day'
                  ? t('notificationManagement.stats.selectDay')
                  : granularity === 'month'
                    ? t('notificationManagement.stats.selectYearMonth')
                    : t('notificationManagement.stats.selectYear')
              }}
            </label>
            <div v-if="granularity === 'day'" class="flex items-center gap-2">
              <input
                v-model="selectedDay"
                type="date"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onDayChange"
              />
            </div>
            <div
              v-else-if="granularity === 'month'"
              class="flex items-center gap-2"
            >
              <select
                v-model="selectedYear"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onMonthYearChange"
              >
                <option v-for="y in yearOptions" :key="y" :value="y">
                  {{ y }}
                </option>
              </select>
              <select
                v-model="selectedMonth"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onMonthYearChange"
              >
                <option v-for="m in 12" :key="m" :value="m">
                  {{ String(m).padStart(2, '0') }}
                </option>
              </select>
            </div>
            <div v-else class="flex items-center gap-2">
              <select
                v-model="selectedYear"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="onYearChange"
              >
                <option v-for="y in yearOptions" :key="y" :value="y">
                  {{ y }}
                </option>
              </select>
            </div>
          </div>
        </div>
        <div class="flex items-end shrink-0">
          <BaseButton
            variant="outline"
            size="sm"
            class="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200 rounded-lg text-sm font-medium"
            @click="fetchStats"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            {{ t('notificationManagement.stats.refreshData') }}
          </BaseButton>
        </div>
      </section>

      <div class="w-full">
        <BaseLoading v-if="loading && !statsData" />

        <div
          v-if="!loading && !statsData"
          class="py-16 text-center rounded-2xl border border-gray-200 bg-white shadow-sm"
        >
          <svg
            class="mx-auto h-12 w-12 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p class="text-sm font-medium text-gray-600">
            {{ t('notificationManagement.stats.noData') }}
          </p>
        </div>

        <template v-else-if="statsData">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-blue-100 text-blue-600 shrink-0"
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
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-blue-600"
                  >TOTAL</span
                >
              </div>
              <div class="text-2xl font-semibold text-gray-900">
                {{ formatNum(statsData.summary?.total) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('notificationManagement.stats.totalDesc') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-green-100 text-green-600 shrink-0"
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-green-600"
                  >SUCCESS</span
                >
              </div>
              <div class="text-2xl font-semibold text-green-600">
                {{ formatNum(statsData.summary?.total_sent) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('notificationManagement.stats.sentDesc') }}
              </div>
              <div
                v-if="successRatePct !== null"
                class="mt-1 text-sm font-medium text-green-600"
              >
                {{ successRatePct }}%
                {{ t('notificationManagement.stats.successRate') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-red-100 text-red-600 shrink-0"
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-red-600"
                  >FAILURE</span
                >
              </div>
              <div class="text-2xl font-semibold text-red-600">
                {{ formatNum(statsData.summary?.total_failed) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('notificationManagement.stats.failedDesc') }}
              </div>
              <div
                v-if="failedRatePct !== null"
                class="mt-1 text-sm font-medium text-red-600"
              >
                {{ failedRatePct }}%
                {{ t('notificationManagement.stats.failureRate') }}
              </div>
            </div>
          </div>

          <div
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[360px] mb-6"
          >
            <h3 class="text-base font-semibold text-gray-900 mb-1">
              {{ t('notificationManagement.stats.seriesTitle') }}
            </h3>
            <p class="text-sm text-gray-500 mb-4">
              {{ t('notificationManagement.stats.seriesSubtitle') }}
            </p>
            <div class="flex-1 min-h-0 flex flex-col">
              <div
                v-if="seriesChartData && seriesChartData.labels.length > 0"
                class="flex-1 min-h-[280px]"
              >
                <Line :data="seriesChartData" :options="seriesChartOptions" />
              </div>
              <div
                v-else
                class="flex-1 min-h-[280px] flex items-center justify-center text-gray-400 text-sm"
              >
                {{ t('notificationManagement.stats.noData') }}
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6 items-stretch">
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[320px]"
            >
              <h3 class="text-base font-semibold text-gray-900 mb-1">
                {{ t('notificationManagement.stats.channelTitle') }}
              </h3>
              <p class="text-sm text-gray-500 mb-3">
                {{ t('notificationManagement.stats.channelSubtitle') }}
              </p>
              <div class="flex-1 min-h-0 overflow-y-auto space-y-5 pr-1">
                <div
                  v-for="(row, idx) in channelBarData"
                  :key="row.provider_type"
                  class="space-y-1.5"
                >
                  <div class="flex items-center justify-between gap-3">
                    <span class="text-sm font-medium text-gray-700 shrink-0">{{
                      row.label
                    }}</span>
                    <span class="flex items-center gap-2 shrink-0">
                      <span class="text-xs font-medium text-gray-500"
                        >{{ row.percent }}%</span
                      >
                      <span class="text-xs font-medium text-gray-900">{{
                        formatNum(row.count)
                      }}</span>
                    </span>
                  </div>
                  <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      :style="{
                        width: row.percent + '%',
                        backgroundColor: row.color
                      }"
                      class="h-full rounded-full transition-all"
                    />
                  </div>
                </div>
              </div>
              <BaseButton
                variant="outline"
                size="sm"
                class="flex-shrink-0 w-full mt-4 flex items-center justify-center py-2.5"
                @click="goToRecords"
              >
                {{ t('notificationManagement.stats.viewReport') }}
              </BaseButton>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 flex flex-col min-h-[320px]"
            >
              <h3 class="text-base font-semibold text-gray-900 mb-3">
                {{ t('notificationManagement.stats.bySource') }}
              </h3>
              <div
                v-if="sourcePieData?.datasets?.[0]?.data?.some((v) => v > 0)"
                class="flex-1 min-h-[260px]"
              >
                <Doughnut :data="sourcePieData" :options="sourcePieOptions" />
              </div>
              <div
                v-else
                class="flex-1 min-h-[260px] flex items-center justify-center text-gray-500 text-sm rounded-lg border border-gray-200 bg-gray-50"
              >
                {{ t('notificationManagement.stats.noData') }}
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  Filler,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { notificationsAdminApi, llmAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

ChartJS.register(
  ArcElement,
  CategoryScale,
  Filler,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const { t } = useI18n()
const router = useRouter()

function formatNum(value) {
  if (value == null || value === '') return '0'
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString() : '0'
}

const statsData = ref(null)
const loading = ref(false)
const granularity = ref('day')
const userScope = ref('')
const userOptions = ref([])
const startDate = ref('')
const endDate = ref('')

const selectedDay = ref('')
const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth() + 1)

const currentYear = new Date().getFullYear()
const yearOptions = computed(() => {
  const arr = []
  for (let y = currentYear; y >= currentYear - 10; y--) arr.push(y)
  return arr
})

const granularityOptions = computed(() => [
  { value: 'day', label: t('notificationManagement.stats.granularityDay') },
  { value: 'month', label: t('notificationManagement.stats.granularityMonth') },
  { value: 'year', label: t('notificationManagement.stats.granularityYear') }
])

const bySource = computed(() => {
  const list = statsData.value?.by_source
  return Array.isArray(list) ? list : []
})

const successRatePct = computed(() => {
  const s = statsData.value?.summary
  if (!s || !s.total) return null
  const rate = (Number(s.total_sent) / Number(s.total)) * 100
  return rate.toFixed(1)
})

const failedRatePct = computed(() => {
  const s = statsData.value?.summary
  if (!s || !s.total) return null
  const rate = (Number(s.total_failed) / Number(s.total)) * 100
  return rate.toFixed(1)
})

const seriesItems = computed(() => {
  const list = statsData.value?.series
  return Array.isArray(list) ? list : []
})

const hasSuccessFailedSeries = computed(() => {
  const first = seriesItems.value[0]
  return first && 'success' in first && 'failed' in first
})

const seriesChartData = computed(() => {
  const list = seriesItems.value
  if (list.length === 0) return null
  if (hasSuccessFailedSeries.value) {
    return {
      labels: list.map((r) => r.bucket || '-'),
      datasets: [
        {
          label: t('notificationManagement.stats.totalSent'),
          data: list.map((r) => r.success ?? 0),
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: t('notificationManagement.stats.totalFailed'),
          data: list.map((r) => r.failed ?? 0),
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          tension: 0.3,
          fill: true
        }
      ]
    }
  }
  return {
    labels: list.map((r) => r.bucket || '-'),
    datasets: [
      {
        label: t('notificationManagement.stats.count'),
        data: list.map((r) => r.count ?? 0),
        borderColor: 'rgb(99, 102, 241)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        tension: 0.3,
        fill: true
      }
    ]
  }
})

const seriesChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      align: 'end',
      labels: { usePointStyle: true, padding: 12 }
    },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        maxTicksLimit: 12,
        maxRotation: 45,
        minRotation: 0,
        font: { size: 11 }
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.06)' },
      ticks: { precision: 0 }
    }
  }
}))

const totalForChannel = computed(() => {
  const list = statsData.value?.by_provider
  if (!Array.isArray(list)) return 0
  return list.reduce((sum, r) => sum + Number(r.count || 0), 0)
})

const CHANNEL_COLORS = ['#3b82f6', '#22c55e', '#eab308', '#a855f7']

const ALL_CHANNELS = [
  { provider_type: 'feishu', label: '飞书' },
  { provider_type: 'wecom', label: 'WeCom' },
  { provider_type: 'wechat', label: '企业微信' },
  { provider_type: 'email', label: 'Email' }
]

const channelBarData = computed(() => {
  const list = statsData.value?.by_provider
  const byType = Array.isArray(list)
    ? Object.fromEntries(
        list.map((r) => [
          r.provider_type,
          {
            count: Number(r.count ?? 0),
            label: r.provider_display_name || r.provider_type
          }
        ])
      )
    : {}
  const total = totalForChannel.value || 1
  return ALL_CHANNELS.map((ch, i) => {
    const data = byType[ch.provider_type]
    const count = data ? data.count : 0
    const label = data?.label || ch.label
    return {
      provider_type: ch.provider_type,
      label,
      count,
      percent: total > 0 ? Math.round((count / total) * 100) : 0,
      color: CHANNEL_COLORS[i % CHANNEL_COLORS.length]
    }
  })
})

const SOURCE_PIE_COLORS = [
  '#3b82f6',
  '#22c55e',
  '#eab308',
  '#a855f7',
  '#ec4899',
  '#06b6d4',
  '#f97316',
  '#84cc16',
  '#6366f1',
  '#14b8a6'
]

const sourcePieData = computed(() => {
  const list = bySource.value
  if (!list.length) return null
  return {
    labels: list.map((r) => {
      const app = r.source_app || '-'
      const type = r.source_type || '-'
      return `${app} / ${type}`
    }),
    datasets: [
      {
        data: list.map((r) => Number(r.count ?? 0)),
        backgroundColor: list.map(
          (_, i) => SOURCE_PIE_COLORS[i % SOURCE_PIE_COLORS.length]
        ),
        borderWidth: 1,
        borderColor: '#fff'
      }
    ]
  }
})

const sourcePieOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right',
      labels: { usePointStyle: true, padding: 10, font: { size: 11 } }
    },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
          const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0
          return `${ctx.label}: ${ctx.raw} (${pct}%)`
        }
      }
    }
  }
}))

function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

async function fetchUserOptions() {
  try {
    const list = await notificationsAdminApi.getUsers()
    if (Array.isArray(list) && list.length > 0) {
      userOptions.value = list.map((u) => ({
        user_id: u.user_id ?? u.id,
        display: (
          u.display ??
          u.username ??
          (u.user_id != null ? `#${u.user_id}` : u.id != null ? `#${u.id}` : '')
        ).toString()
      }))
      return
    }
  } catch {
    /* fallback to admin users list */
  }
  try {
    const data = await llmAdminApi.getUsers({ page_size: 200 })
    const raw = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : []
    userOptions.value = raw.map((u) => ({
      user_id: u.id ?? u.user_id,
      display: (
        u.username ??
        u.display ??
        u.email ??
        (u.id != null ? `#${u.id}` : '')
      ).toString()
    }))
  } catch {
    userOptions.value = []
  }
}

function setDefaultDates() {
  const now = new Date()
  const todayStr = formatDate(now)
  const g = granularity.value
  if (g === 'day') {
    selectedDay.value = todayStr
    startDate.value = todayStr
    endDate.value = todayStr
  } else if (g === 'month') {
    selectedYear.value = now.getFullYear()
    selectedMonth.value = now.getMonth() + 1
    startDate.value = `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}-01`
    const last = new Date(selectedYear.value, selectedMonth.value, 0)
    endDate.value = formatDate(last)
  } else {
    selectedYear.value = now.getFullYear()
    startDate.value = `${selectedYear.value}-01-01`
    endDate.value = `${selectedYear.value}-12-31`
  }
}

function onDayChange() {
  if (!selectedDay.value) return
  startDate.value = selectedDay.value
  endDate.value = selectedDay.value
  fetchStats()
}

function onMonthYearChange() {
  const y = selectedYear.value
  const m = selectedMonth.value
  if (!y || !m) return
  startDate.value = `${y}-${String(m).padStart(2, '0')}-01`
  const last = new Date(y, m, 0)
  endDate.value = formatDate(last)
  fetchStats()
}

function onYearChange() {
  const y = selectedYear.value
  if (!y) return
  startDate.value = `${y}-01-01`
  endDate.value = `${y}-12-31`
  fetchStats()
}

function selectGranularity(g) {
  granularity.value = g
  setDefaultDates()
  fetchStats()
}

async function fetchStats() {
  if (!startDate.value || !endDate.value) {
    setDefaultDates()
  }
  loading.value = true
  try {
    const params = { granularity: granularity.value }
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
    if (userScope.value) params.user_id = userScope.value
    const data = await notificationsAdminApi.getStats(params)
    statsData.value = data ?? null
  } catch {
    statsData.value = null
  } finally {
    loading.value = false
  }
}

function goToRecords() {
  router.push({ name: 'AdminNotificationsRecords' })
}

onMounted(() => {
  fetchUserOptions()
  setDefaultDates()
  fetchStats()
})
</script>
