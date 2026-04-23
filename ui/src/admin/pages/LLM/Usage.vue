<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('llm.usage.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('llm.usage.subtitle') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-sm text-gray-600 whitespace-nowrap">{{
                t('llm.usage.filterByUser')
              }}</span>
              <select
                v-model="selectedUserId"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-56 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                @change="onFiltersChanged"
              >
                <option value="">{{ t('llm.usage.allUsers') }}</option>
                <option v-for="u in userOptions" :key="u.id" :value="u.id">
                  {{ u.label }}
                </option>
              </select>
              <input
                v-model="filters.model"
                type="text"
                :placeholder="t('llm.usage.filterModel')"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-44 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                @input="onModelInput"
              />
              <select
                v-model="filters.success"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-28 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 bg-white"
                @change="onFiltersChanged"
              >
                <option value="">{{ t('llm.usage.filterSuccess') }}</option>
                <option value="true">{{ t('common.yes') }}</option>
                <option value="false">{{ t('common.no') }}</option>
              </select>
              <span class="text-sm text-gray-600 whitespace-nowrap">{{
                t('llm.usage.dateRange')
              }}</span>
              <input
                v-model="filters.startDate"
                type="date"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="onFiltersChanged"
              />
              <span class="text-gray-400">–</span>
              <input
                v-model="filters.endDate"
                type="date"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="onFiltersChanged"
              />
            </div>
            <BaseButton
              variant="outline"
              size="sm"
              :loading="loading"
              :title="t('common.refresh')"
              class="flex items-center gap-1 shadow-sm hover:shadow-md transition-shadow"
              @click="fetchList"
            >
              <svg
                v-if="!loading"
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
              <span class="sr-only">{{ t('common.refresh') }}</span>
            </BaseButton>
          </div>

          <BaseLoading v-if="loading && !items.length" />

          <div
            v-if="!loading && !items.length"
            class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
          >
            <p class="text-sm font-medium text-gray-600">
              {{ t('common.noData') }}
            </p>
          </div>

          <template v-if="!loading && items.length > 0">
            <div
              class="overflow-x-auto relative rounded-lg border border-gray-200 bg-white shadow-sm"
            >
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.time') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.user') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.model') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.promptTokens') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.completionTokens') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.totalTokens') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.e2eLatency') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.ttftSec') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.outputTps') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.costUsd') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                    >
                      {{ t('llm.usage.success') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="u in items"
                    :key="u.id"
                    class="hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
                    @click="openDetail(u)"
                  >
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-500"
                    >
                      {{ formatDate(u.created_at) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-500"
                    >
                      {{ u.username || u.user_id || '-' }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >
                      {{ u.model || '–' }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-500"
                    >
                      {{ formatNum(u.prompt_tokens) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-500"
                    >
                      {{ formatNum(u.completion_tokens) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-500"
                    >
                      {{ formatNum(u.total_tokens) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ formatE2eLatency(u.e2e_latency_sec) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ formatTtft(u.ttft_sec) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ formatOutputTps(u.output_tps) }}
                    </td>
                    <td
                      class="px-4 py-4 whitespace-nowrap text-sm text-amber-600 font-medium"
                    >
                      {{ formatCost(u.cost, u.cost_currency) }}
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <span
                        :class="
                          u.success
                            ? 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800'
                            : 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800'
                        "
                      >
                        {{ u.success ? t('common.yes') : t('common.no') }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div
              v-if="total > 0"
              class="mt-6 pt-4 border-t border-gray-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
            >
              <div class="text-sm text-gray-700 font-medium">
                {{
                  t('common.pagination.showing', {
                    from: formatNum((page - 1) * pageSize + 1),
                    to: formatNum(Math.min(page * pageSize, total)),
                    total: formatNum(total)
                  })
                }}
              </div>
              <div class="flex items-center gap-3 flex-wrap">
                <label class="text-sm text-gray-600"
                  >{{ t('common.pagination.itemsPerPage') }}:</label
                >
                <select
                  v-model.number="pageSize"
                  class="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  @change="handlePageSizeChange"
                >
                  <option :value="10">10</option>
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="page <= 1"
                  @click="goPrevPage"
                  >{{ t('common.pagination.previous') }}</BaseButton
                >
                <span
                  class="text-sm text-gray-700 font-semibold px-3 py-1.5 bg-gray-50 rounded-md border border-gray-200"
                >
                  {{
                    t('common.pagination.page', {
                      current: page,
                      total: totalPages
                    })
                  }}
                </span>
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="page >= totalPages"
                  @click="goNextPage"
                  >{{ t('common.pagination.next') }}</BaseButton
                >
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Detail drawer (right slide-out, same style as Records detail panel) -->
      <Transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="detailVisible"
          class="fixed inset-0 bg-gray-900 bg-opacity-50 z-40"
          aria-hidden="true"
          @click="closeDetail"
        />
      </Transition>
      <Transition
        enter-active-class="transition-transform duration-300 ease-out"
        enter-from-class="translate-x-full"
        enter-to-class="translate-x-0"
        leave-active-class="transition-transform duration-250 ease-in"
        leave-from-class="translate-x-0"
        leave-to-class="translate-x-full"
      >
        <div
          v-if="detailVisible"
          class="fixed inset-y-0 right-0 w-full max-w-2xl bg-white shadow-xl z-50 flex flex-col"
          role="dialog"
          aria-modal="true"
          :aria-label="t('llm.usage.detailTitle')"
        >
          <div
            class="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 flex-shrink-0"
          >
            <h2 class="text-lg font-semibold text-gray-900">
              {{ t('llm.usage.detailTitle') }}
            </h2>
            <button
              type="button"
              class="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              :aria-label="t('common.close')"
              @click="closeDetail"
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
            v-if="selectedDetail"
            class="flex-1 overflow-y-auto p-6 space-y-6"
          >
            <div>
              <h3 class="text-sm font-semibold text-gray-900 mb-4">
                {{ t('llm.usage.basicInfo') }}
              </h3>
              <dl class="grid grid-cols-1 gap-4">
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.time') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatDate(selectedDetail.created_at) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.startedAt') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{
                      selectedDetail.started_at
                        ? formatDate(selectedDetail.started_at)
                        : '–'
                    }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.user') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{
                      selectedDetail.username || selectedDetail.user_id || '–'
                    }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.configModel') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ selectedDetail.model || '–' }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.responseModel') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{
                      selectedDetail.metadata &&
                      selectedDetail.metadata.response_model
                        ? selectedDetail.metadata.response_model
                        : '–'
                    }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.promptTokens') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatNum(selectedDetail.prompt_tokens) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.completionTokens') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatNum(selectedDetail.completion_tokens) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.totalTokens') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatNum(selectedDetail.total_tokens) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.e2eLatency') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatE2eLatency(selectedDetail.e2e_latency_sec) }}
                  </dd>
                </div>
                <div v-if="selectedDetail.ttft_sec != null">
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.ttftSec') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatTtft(selectedDetail.ttft_sec) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.outputTps') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{ formatOutputTps(selectedDetail.output_tps) }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.costUsd') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{
                      formatCost(
                        selectedDetail.cost,
                        selectedDetail.cost_currency
                      )
                    }}
                  </dd>
                </div>
                <div>
                  <dt
                    class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                  >
                    {{ t('llm.usage.success') }}
                  </dt>
                  <dd class="text-sm font-medium text-gray-900">
                    {{
                      selectedDetail.success ? t('common.yes') : t('common.no')
                    }}
                  </dd>
                </div>
              </dl>
            </div>
            <div
              v-if="selectedDetail.error"
              class="border-t border-gray-200 pt-6"
            >
              <h3 class="text-sm font-semibold text-gray-900 mb-4">
                {{ t('llm.usage.error') }}
              </h3>
              <div
                class="rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm"
              >
                <pre
                  class="text-xs font-mono text-red-800 whitespace-pre-wrap break-words"
                  >{{ selectedDetail.error }}</pre
                >
              </div>
            </div>
            <div
              v-if="
                selectedDetail.metadata &&
                Object.keys(selectedDetail.metadata).length
              "
              class="border-t border-gray-200 pt-6"
            >
              <h3 class="text-sm font-semibold text-gray-900 mb-4">
                {{ t('llm.usage.metadata') }}
              </h3>
              <div
                class="rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm"
              >
                <pre
                  class="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words"
                  >{{ JSON.stringify(selectedDetail.metadata, null, 2) }}</pre
                >
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDebounce } from '@/composables/useDebounce'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import {
  formatNumLocale,
  formatCostLocale,
  formatDateIsoLocale
} from '@/utils/formatting'
import { llmAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t, locale } = useI18n()
const { showError } = useToast()

function formatNum(value) {
  return formatNumLocale(value, locale.value)
}

function formatCost(value, currency = 'USD') {
  return formatCostLocale(value, currency, locale.value)
}

function formatDate(iso) {
  return formatDateIsoLocale(iso, locale.value)
}

function formatE2eLatency(sec) {
  if (sec == null || typeof sec !== 'number') return '–'
  if (sec < 1) return `${(sec * 1000).toFixed(0)} ms`
  return `${sec.toFixed(2)} s`
}

function formatTtft(sec) {
  if (sec == null || typeof sec !== 'number') return '–'
  if (sec < 1) return `${(sec * 1000).toFixed(0)} ms`
  return `${sec.toFixed(2)} s`
}

function formatOutputTps(tps) {
  if (tps == null || typeof tps !== 'number') return '–'
  return `${tps.toFixed(2)} tok/s`
}

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filters = reactive({ model: '', success: '', startDate: '', endDate: '' })
const userOptions = ref([])
const selectedUserId = ref('')
const detailVisible = ref(false)
const selectedDetail = ref(null)

function openDetail(record) {
  selectedDetail.value = record
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  selectedDetail.value = null
}

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

function onFiltersChanged() {
  page.value = 1
  fetchList()
}

function applyModelFilter() {
  page.value = 1
  fetchList()
}

async function handlePageSizeChange() {
  page.value = 1
  await fetchList()
}

const { debouncedFn: onModelInput, cancel: cancelDebounce } = useDebounce(
  applyModelFilter,
  300
)

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize.value))
)

function goPrevPage() {
  if (page.value <= 1) return
  page.value -= 1
  fetchList()
}

function goNextPage() {
  if (page.value >= totalPages.value) return
  page.value += 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (selectedUserId.value) params.user_id = selectedUserId.value
    if (filters.model) params.model = filters.model
    if (filters.success) params.success = filters.success
    if (filters.startDate) params.start_date = filters.startDate
    if (filters.endDate) params.end_date = filters.endDate
    const data = await llmAdminApi.getLLMUsage(params)
    items.value = data?.results ?? []
    total.value = data?.total ?? 0
  } catch (err) {
    showError(extractErrorMessage(err, t('common.error')))
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const now = new Date()
  const end = new Date(now)
  const start = new Date(now)
  start.setDate(start.getDate() - 3)
  const pad = (n) => String(n).padStart(2, '0')
  filters.startDate = `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`
  filters.endDate = `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}`
  fetchUserOptions()
  fetchList()
})

onUnmounted(() => {
  cancelDebounce()
})
</script>
