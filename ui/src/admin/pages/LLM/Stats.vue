<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('llm.stats.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('llm.stats.subtitle') }}
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
              {{ t('llm.stats.filterByUser') }}
            </label>
            <select
              v-model="selectedUserId"
              class="rounded-lg border border-gray-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 min-w-[140px] hover:border-gray-300 transition-colors"
              @change="fetchStats"
            >
              <option value="">{{ t('llm.stats.allUsers') }}</option>
              <option v-for="u in userOptions" :key="u.id" :value="u.id">
                {{ u.label }}
              </option>
            </select>
          </div>
          <div class="flex flex-col gap-1.5">
            <label
              class="text-[10px] font-bold text-gray-400 uppercase tracking-wider ml-1"
            >
              {{ t('llm.stats.granularity') }}
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
                  ? t('llm.stats.selectDay')
                  : granularity === 'month'
                    ? t('llm.stats.selectYearMonth')
                    : t('llm.stats.selectYear')
              }}
            </label>
            <template v-if="granularity === 'day'">
              <input
                v-model="selectedDate"
                type="date"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="fetchStats"
              />
            </template>
            <template v-else-if="granularity === 'month'">
              <input
                v-model="selectedMonth"
                type="month"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="fetchStats"
              />
            </template>
            <template v-else-if="granularity === 'year'">
              <select
                v-model.number="selectedYear"
                class="rounded-lg border border-gray-200 px-3 py-2 text-sm w-24 bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-primary-600 hover:border-gray-300 transition-colors"
                @change="fetchStats"
              >
                <option v-for="y in yearOptions" :key="y" :value="y">
                  {{ y }}
                </option>
              </select>
            </template>
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
            {{ t('llm.stats.refreshData') }}
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
            {{ t('llm.stats.noData') }}
          </p>
        </div>

        <template v-else-if="statsData">
          <section
            class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-6"
          >
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-indigo-100 text-indigo-600 shrink-0"
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
                      d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343L12.657 5.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-indigo-600"
                  >TOKENS</span
                >
              </div>
              <div class="text-2xl font-semibold text-gray-900">
                {{ formatNum(statsData.summary?.total_tokens) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('llm.stats.totalTokens') }}
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
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-green-600"
                  >CALLS</span
                >
              </div>
              <div class="text-2xl font-semibold text-green-600">
                {{ formatNum(statsData.summary?.total_calls) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('llm.stats.totalCalls') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-amber-100 text-amber-600 shrink-0"
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
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </span>
                <span class="text-xs font-medium uppercase text-amber-600"
                  >COST</span
                >
              </div>
              <div class="text-2xl font-semibold text-amber-600">
                {{
                  formatCost(
                    statsData.summary?.total_cost,
                    statsData.summary?.total_cost_currency
                  )
                }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('llm.stats.totalCostUsd') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-purple-100 text-purple-600 shrink-0"
                >
                  <span class="text-sm font-bold">P</span>
                </span>
                <span class="text-xs font-medium uppercase text-purple-600"
                  >PROMPT</span
                >
              </div>
              <div class="text-2xl font-semibold text-purple-600">
                {{ formatNum(statsData.summary?.total_prompt_tokens) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('llm.stats.promptTokens') }}
              </div>
            </div>
            <div
              class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5"
            >
              <div class="flex items-center justify-between mb-2">
                <span
                  class="flex items-center justify-center w-9 h-9 rounded-full bg-orange-100 text-orange-600 shrink-0"
                >
                  <span class="text-sm font-bold">C</span>
                </span>
                <span class="text-xs font-medium uppercase text-orange-600"
                  >COMPLETION</span
                >
              </div>
              <div class="text-2xl font-semibold text-orange-600">
                {{ formatNum(statsData.summary?.total_completion_tokens) }}
              </div>
              <div class="text-sm text-gray-500 mt-0.5">
                {{ t('llm.stats.completionTokens') }}
              </div>
            </div>
          </section>

          <section
            v-if="
              seriesByModelTokensChartData ||
              seriesByModelCostChartData ||
              byModel.length
            "
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 mb-6"
          >
            <div
              v-if="seriesByModelTokensChartData || seriesByModelCostChartData"
              class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6"
            >
              <div
                v-if="seriesByModelTokensChartData"
                class="flex flex-col min-h-[280px]"
              >
                <h3 class="text-base font-semibold text-gray-900 mb-1">
                  {{ t('llm.stats.chartByModelTokens') }}
                </h3>
                <p class="text-sm text-gray-500 mb-3">{{ chartSubtitle }}</p>
                <div class="flex-1 min-h-[240px]">
                  <Line
                    :data="seriesByModelTokensChartData"
                    :options="lineChartOptions"
                  />
                </div>
              </div>
              <div
                v-if="seriesByModelCostChartData"
                class="flex flex-col min-h-[280px]"
              >
                <h3 class="text-base font-semibold text-gray-900 mb-1">
                  {{ t('llm.stats.chartByModelCost') }}
                </h3>
                <p class="text-sm text-gray-500 mb-3">{{ chartSubtitle }}</p>
                <div class="flex-1 min-h-[240px]">
                  <Line
                    :data="seriesByModelCostChartData"
                    :options="lineChartOptions"
                  />
                </div>
              </div>
            </div>
            <div v-if="byModel.length">
              <h3 class="text-base font-semibold text-gray-900 mb-3">
                {{ t('llm.stats.byModel') }}
              </h3>
              <div class="overflow-x-auto rounded-lg border border-gray-200">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.model') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.totalTokens') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.totalCostUsd') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.promptTokens') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.completionTokens') }}
                      </th>
                      <th
                        class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                      >
                        {{ t('llm.stats.totalCalls') }}
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-100">
                    <tr
                      v-for="row in byModel"
                      :key="row.model || row.name"
                      class="hover:bg-gray-50 transition-colors duration-150"
                    >
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900"
                      >
                        {{ row.model ?? row.name ?? '-' }}
                      </td>
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm text-gray-500"
                      >
                        {{ formatNum(row.total_tokens) }}
                      </td>
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm text-amber-600 font-medium"
                      >
                        {{
                          formatCost(row.total_cost, row.total_cost_currency)
                        }}
                      </td>
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm text-gray-500"
                      >
                        {{ formatNum(row.total_prompt_tokens) }}
                      </td>
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm text-gray-500"
                      >
                        {{ formatNum(row.total_completion_tokens) }}
                      </td>
                      <td
                        class="px-4 py-3 whitespace-nowrap text-sm text-gray-500"
                      >
                        {{ formatNum(row.total_calls ?? row.count) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section
            v-if="
              seriesByModelE2eChartData ||
              seriesByModelTtftChartData ||
              seriesByModelOutputTpsChartData
            "
            class="rounded-2xl bg-white border border-gray-200 shadow-sm p-5 mb-6"
          >
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div
                v-if="seriesByModelE2eChartData"
                class="flex flex-col min-h-[280px]"
              >
                <h3 class="text-base font-semibold text-gray-900 mb-1">
                  {{ t('llm.stats.chartByModelE2e') }}
                </h3>
                <p class="text-sm text-gray-500 mb-3">{{ chartSubtitle }}</p>
                <div class="flex-1 min-h-[240px]">
                  <Line
                    :data="seriesByModelE2eChartData"
                    :options="lineChartOptions"
                  />
                </div>
              </div>
              <div
                v-if="seriesByModelTtftChartData"
                class="flex flex-col min-h-[280px]"
              >
                <h3 class="text-base font-semibold text-gray-900 mb-1">
                  {{ t('llm.stats.chartByModelTtft') }}
                </h3>
                <p class="text-sm text-gray-500 mb-3">{{ chartSubtitle }}</p>
                <div class="flex-1 min-h-[240px]">
                  <Line
                    :data="seriesByModelTtftChartData"
                    :options="lineChartOptions"
                  />
                </div>
              </div>
            </div>
            <div
              v-if="seriesByModelOutputTpsChartData"
              class="flex flex-col min-h-[280px]"
            >
              <h3 class="text-base font-semibold text-gray-900 mb-1">
                {{ t('llm.stats.chartByModelOutputTps') }}
              </h3>
              <p class="text-sm text-gray-500 mb-3">{{ chartSubtitle }}</p>
              <div class="flex-1 min-h-[240px]">
                <Line
                  :data="seriesByModelOutputTpsChartData"
                  :options="lineChartOptions"
                />
              </div>
            </div>
          </section>
        </template>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Filler,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Line } from 'vue-chartjs'
import { formatNumLocale, formatCostLocale } from '@/utils/formatting'
import { llmAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Filler,
  Title,
  Tooltip,
  Legend
)

const { t, locale } = useI18n()

function formatNum(value) {
  const s = formatNumLocale(value, locale.value)
  return s === '-' ? '0' : s
}

function formatCost(value, currency = 'USD') {
  return formatCostLocale(value, currency, locale.value)
}

const statsData = ref(null)
const loading = ref(false)
const userOptions = ref([])
const selectedUserId = ref('')
const selectedDate = ref('')
const selectedMonth = ref('')
const selectedYear = ref(new Date().getFullYear())
const granularity = ref('day')

function toUserLabel(u) {
  const parts = []
  if (u.username) parts.push(u.username)
  if (u.email) parts.push(u.email)
  if (u.nickname) parts.push(u.nickname)
  if (parts.length === 0 && u.id) parts.push(String(u.id))
  return parts.join(' · ')
}

async function fetchUserOptions() {
  try {
    const data = await llmAdminApi.getUsers({ page_size: 200 })
    const list = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : []
    userOptions.value = list.map((u) => ({ id: u.id, label: toUserLabel(u) }))
  } catch {
    userOptions.value = []
  }
}

function selectGranularity(g) {
  granularity.value = g
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  selectedDate.value = `${y}-${m}-${d}`
  selectedMonth.value = `${y}-${m}`
  selectedYear.value = y
  fetchStats()
}

function lastDayOfMonth(ym) {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(y, m, 0).getDate()
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

const yearOptions = computed(() => {
  const current = new Date().getFullYear()
  return Array.from({ length: 10 }, (_, i) => current - i)
})

const granularityOptions = computed(() => [
  { value: 'day', label: t('llm.stats.granularityDay') },
  { value: 'month', label: t('llm.stats.granularityMonth') },
  { value: 'year', label: t('llm.stats.granularityYear') }
])

const byModel = computed(() => {
  const list = statsData.value?.by_model
  return Array.isArray(list) ? list : []
})

const seriesItems = computed(() => {
  const s = statsData.value?.series
  return Array.isArray(s?.items) ? s.items : []
})

const expectedBuckets = computed(() => {
  const buckets = statsData.value?.expected_buckets
  if (Array.isArray(buckets) && buckets.length > 0) return buckets
  return seriesItems.value.map((i) => i.bucket).filter(Boolean)
})

const seriesByModel = computed(() => {
  const list = statsData.value?.series_by_model
  return Array.isArray(list) ? list : []
})

const chartSubtitle = computed(() => {
  const g = statsData.value?.series?.granularity || granularity.value
  if (g === 'day') return t('llm.stats.chartByHour')
  if (g === 'month') return t('llm.stats.chartByDay')
  if (g === 'year') return t('llm.stats.chartByMonth')
  return ''
})

function formatBucketLabel(bucketIso) {
  if (!bucketIso) return ''
  try {
    const d = new Date(bucketIso)
    const g = statsData.value?.series?.granularity || granularity.value
    if (g === 'day')
      return d.toLocaleTimeString(locale.value, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })
    if (g === 'month')
      return d.toLocaleDateString(locale.value, {
        month: '2-digit',
        day: '2-digit'
      })
    if (g === 'year')
      return d.toLocaleDateString(locale.value, {
        year: 'numeric',
        month: '2-digit'
      })
  } catch {
    return bucketIso
  }
  return bucketIso
}

const MODEL_CHART_COLORS = [
  { border: 'rgb(99, 102, 241)', fill: 'rgba(99, 102, 241, 0.1)' },
  { border: 'rgb(34, 197, 94)', fill: 'rgba(34, 197, 94, 0.1)' },
  { border: 'rgb(239, 68, 68)', fill: 'rgba(239, 68, 68, 0.1)' },
  { border: 'rgb(245, 158, 11)', fill: 'rgba(245, 158, 11, 0.1)' },
  { border: 'rgb(139, 92, 246)', fill: 'rgba(139, 92, 246, 0.1)' },
  { border: 'rgb(6, 182, 212)', fill: 'rgba(6, 182, 212, 0.1)' }
]

function buildSeriesByModelChartData(valueKey, options = {}) {
  const { useNullForMissing = false, fill = true } = options
  const keys = expectedBuckets.value
  if (keys.length === 0) return null
  const labels = keys.map((b) => formatBucketLabel(b))
  const list = seriesByModel.value
  const byModel = new Map()
  for (const r of list) {
    const m = r.model || '-'
    if (!byModel.has(m)) byModel.set(m, new Map())
    const val = r[valueKey]
    byModel
      .get(m)
      .set(
        r.bucket,
        val !== undefined && val !== null ? val : useNullForMissing ? null : 0
      )
  }
  const datasets = []
  let idx = 0
  byModel.forEach((bucketValues, model) => {
    const data = keys.map((b) => {
      const v = bucketValues.get(b)
      return v !== undefined ? v : useNullForMissing ? null : 0
    })
    const colors = MODEL_CHART_COLORS[idx % MODEL_CHART_COLORS.length]
    datasets.push({
      label: model,
      data,
      borderColor: colors.border,
      backgroundColor: colors.fill,
      tension: 0.3,
      fill,
      spanGaps: false
    })
    idx += 1
  })
  return {
    labels,
    datasets
  }
}

const seriesByModelTokensChartData = computed(() =>
  buildSeriesByModelChartData('total_tokens')
)
const seriesByModelCostChartData = computed(() =>
  buildSeriesByModelChartData('total_cost')
)
const seriesByModelE2eChartData = computed(() =>
  buildSeriesByModelChartData('avg_e2e_latency_sec', { fill: false })
)
const seriesByModelTtftChartData = computed(() =>
  buildSeriesByModelChartData('avg_ttft_sec', { fill: false })
)
const seriesByModelOutputTpsChartData = computed(() =>
  buildSeriesByModelChartData('avg_output_tps', { fill: false })
)

const lineChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      align: 'end',
      labels: {
        usePointStyle: true,
        pointStyle: 'circle',
        boxWidth: 8,
        boxHeight: 8,
        padding: 4,
        font: { size: 10 }
      }
    },
    tooltip: { mode: 'index', intersect: false }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        maxRotation: 45,
        minRotation: 0,
        maxTicksLimit: 14,
        font: { size: 10 }
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.06)' },
      ticks: { font: { size: 10 } }
    }
  }
}))

async function fetchStats() {
  loading.value = true
  try {
    const params = { granularity: granularity.value }
    let start = ''
    let end = ''
    if (granularity.value === 'day') {
      start = selectedDate.value
      end = selectedDate.value
    } else if (granularity.value === 'month') {
      start = selectedMonth.value ? `${selectedMonth.value}-01` : ''
      end = selectedMonth.value ? lastDayOfMonth(selectedMonth.value) : ''
    } else if (granularity.value === 'year') {
      start = selectedYear.value ? `${selectedYear.value}-01-01` : ''
      end = selectedYear.value ? `${selectedYear.value}-12-31` : ''
    }
    if (start) params.start_date = start
    if (end) params.end_date = end
    if (selectedUserId.value) params.user_id = selectedUserId.value
    if (start && end) params.use_series = 1
    const data = await llmAdminApi.getTokenStats(params)
    statsData.value = data ?? null
  } catch {
    statsData.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  selectedDate.value = `${y}-${m}-${d}`
  selectedMonth.value = `${y}-${m}`
  selectedYear.value = y
  fetchUserOptions()
  fetchStats()
})
</script>
