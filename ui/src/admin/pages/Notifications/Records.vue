<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('notificationManagement.records.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('notificationManagement.records.subtitle') }}
        </p>
      </div>

      <div
        class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
      >
        <div class="p-6">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
            <div class="flex flex-wrap items-center gap-3">
              <input
                v-model="filters.source_app"
                type="text"
                :placeholder="t('notificationManagement.records.sourceApp')"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-40 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @input="onFiltersChanged"
              />
              <input
                v-model="filters.source_type"
                type="text"
                :placeholder="t('notificationManagement.records.sourceType')"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-40 focus:outline-none focus:ring-1 focus:ring-primary-500"
                @input="onFiltersChanged"
              />
              <select
                v-model="filters.status"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm w-36 bg-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="onFiltersChanged"
              >
                <option value="">
                  {{ t('notificationManagement.records.statusAll') }}
                </option>
                <option value="success">
                  {{ t('notificationManagement.records.statusSuccess') }}
                </option>
                <option value="failed">
                  {{ t('notificationManagement.records.statusFailed') }}
                </option>
                <option value="merged">
                  {{ t('notificationManagement.records.statusMerged') }}
                </option>
                <option value="silenced">
                  {{ t('notificationManagement.records.statusSilenced') }}
                </option>
                <option value="pending">
                  {{ t('notificationManagement.records.statusPending') }}
                </option>
              </select>
              <input
                v-model="filters.start_date"
                type="date"
                :max="filters.end_date || undefined"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="onFiltersChanged"
              />
              <span class="text-gray-400">–</span>
              <input
                v-model="filters.end_date"
                type="date"
                :min="filters.start_date || undefined"
                class="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                @change="onFiltersChanged"
              />
            </div>
            <div class="flex items-center gap-2">
              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                :title="t('common.refresh')"
                class="flex items-center gap-1 shadow-sm hover:shadow-md transition-shadow"
                @click="fetchRecords"
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
              <BaseButton
                variant="outline"
                size="sm"
                class="flex items-center gap-1"
                @click="resetFilters"
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
                {{ t('notificationManagement.records.resetFilters') }}
              </BaseButton>
            </div>
          </div>

          <BaseLoading v-if="loading && records.length === 0" />

          <div
            v-else-if="!loading && records.length === 0"
            class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p class="text-sm font-medium text-gray-600">
              {{ t('notificationManagement.records.noRecords') }}
            </p>
          </div>

          <template v-else>
            <div class="overflow-x-auto rounded-lg border border-gray-200">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sourceApp') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sourceType') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sourceId') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.provider') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.status') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.createdAt') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sentAt') }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.user') }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                  <tr
                    v-for="r in records"
                    :key="r.uuid"
                    class="hover:bg-gray-50 cursor-pointer transition-colors"
                    @click="openDetail(r.uuid)"
                  >
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-900"
                    >
                      {{ r.source_app || '-' }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ r.source_type || '-' }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 font-mono"
                    >
                      {{ r.source_id || '-' }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ r.provider_display_name || r.provider_type || '-' }}
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap">
                      <span :class="statusClass(r.status)">{{
                        r.status || '-'
                      }}</span>
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ formatDate(r.created_at) }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ formatDate(r.sent_at) }}
                    </td>
                    <td
                      class="px-4 py-3 whitespace-nowrap text-sm text-gray-600"
                    >
                      {{ r.user_display ?? r.user_id ?? '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div
              v-if="total > pageSize"
              class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 pt-4"
            >
              <p class="text-sm text-gray-600">
                {{
                  t('common.pagination.showing', {
                    from: (page - 1) * pageSize + 1,
                    to: Math.min(page * pageSize, total),
                    total
                  })
                }}
              </p>
              <div class="flex items-center gap-2">
                <select
                  v-model.number="pageSize"
                  class="rounded-md border border-gray-300 px-2 py-1 text-sm"
                  @change="handlePageSizeChange"
                >
                  <option :value="10">10</option>
                  <option :value="20">20</option>
                  <option :value="50">50</option>
                  <option :value="100">100</option>
                </select>
                <span class="text-sm text-gray-500">{{
                  t('notificationManagement.records.pageSize')
                }}</span>
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="page <= 1"
                  :title="t('common.pagination.previous')"
                  class="flex items-center gap-1"
                  @click="goToPreviousPage"
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
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                  <span class="sr-only">{{
                    t('common.pagination.previous')
                  }}</span>
                </BaseButton>
                <BaseButton
                  variant="outline"
                  size="sm"
                  :disabled="page >= totalPages"
                  :title="t('common.pagination.next')"
                  class="flex items-center gap-1"
                  @click="goToNextPage"
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
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                  <span class="sr-only">{{ t('common.pagination.next') }}</span>
                </BaseButton>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Record detail right panel -->
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
          :aria-label="t('notificationManagement.records.detailTitle')"
        >
          <div
            class="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 flex-shrink-0"
          >
            <h2 class="text-lg font-semibold text-gray-900">
              {{ t('notificationManagement.records.detailTitle') }}
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
          <div class="flex-1 overflow-y-auto p-6 space-y-6">
            <BaseLoading v-if="detailLoading" />
            <template v-else-if="detailRecord">
              <div>
                <h3 class="text-sm font-semibold text-gray-900 mb-4">
                  {{ t('notificationManagement.records.basicInfo') }}
                </h3>
                <dl class="grid grid-cols-1 gap-4">
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sourceApp') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{ detailRecord.source_app || '-' }}
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sourceType') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{ detailRecord.source_type || '-' }}
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.provider') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{
                        detailRecord.provider_display_name ||
                        detailRecord.provider_type ||
                        '-'
                      }}
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.status') }}
                    </dt>
                    <dd>
                      <span
                        :class="statusClass(detailRecord.status)"
                        class="text-sm font-medium"
                        >{{ detailRecord.status || '-' }}</span
                      >
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.user') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{
                        detailRecord.user_display ?? detailRecord.user_id ?? '-'
                      }}
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.createdAt') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{ formatDate(detailRecord.created_at) }}
                    </dd>
                  </div>
                  <div>
                    <dt
                      class="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider"
                    >
                      {{ t('notificationManagement.records.sentAt') }}
                    </dt>
                    <dd class="text-sm font-medium text-gray-900">
                      {{ formatDate(detailRecord.sent_at) }}
                    </dd>
                  </div>
                </dl>
              </div>
              <div
                v-if="detailRecord.error_message"
                class="border-t border-gray-200 pt-6"
              >
                <h3 class="text-sm font-semibold text-gray-900 mb-4">
                  {{ t('notificationManagement.records.errorMessage') }}
                </h3>
                <div
                  class="rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm"
                >
                  <pre
                    class="text-xs font-mono text-red-800 whitespace-pre-wrap break-words"
                    >{{ detailRecord.error_message }}</pre
                  >
                </div>
              </div>
              <div
                v-if="
                  detailRecord.payload &&
                  Object.keys(detailRecord.payload).length
                "
                class="border-t border-gray-200 pt-6"
              >
                <h3 class="text-sm font-semibold text-gray-900 mb-4">
                  {{ t('notificationManagement.records.payload') }}
                </h3>
                <div
                  class="rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm"
                >
                  <pre
                    class="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words"
                    >{{ JSON.stringify(detailRecord.payload, null, 2) }}</pre
                  >
                </div>
              </div>
              <div
                v-if="detailRecord.response != null"
                class="border-t border-gray-200 pt-6"
              >
                <h3 class="text-sm font-semibold text-gray-900 mb-4">
                  {{ t('notificationManagement.records.response') }}
                </h3>
                <div
                  class="rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm"
                >
                  <pre
                    class="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words"
                    >{{
                      typeof detailRecord.response === 'object'
                        ? JSON.stringify(detailRecord.response, null, 2)
                        : detailRecord.response
                    }}</pre
                  >
                </div>
              </div>
            </template>
            <p v-else class="text-sm text-gray-500">
              {{ t('notificationManagement.records.detailNotFound') }}
            </p>
          </div>
        </div>
      </Transition>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { useDebounceFn } from '@vueuse/core'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import { notificationsAdminApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const { t } = useI18n()
const { showError } = useToast()

const loading = ref(false)
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailRecord = ref(null)
const selectedRecordUuid = ref(null)

function getDefaultDetailDateRange() {
  const now = new Date()
  const endStr = format(now, 'yyyy-MM-dd')
  const start = new Date(now)
  start.setDate(start.getDate() - 3)
  return { start_date: format(start, 'yyyy-MM-dd'), end_date: endStr }
}

const defaultDateRange = getDefaultDetailDateRange()
const filters = ref({
  source_app: '',
  source_type: '',
  status: '',
  start_date: defaultDateRange.start_date,
  end_date: defaultDateRange.end_date
})

const totalPages = computed(() =>
  total.value > 0 ? Math.ceil(total.value / pageSize.value) : 1
)

function formatDate(val) {
  if (!val) return '-'
  try {
    return format(new Date(val), 'yyyy-MM-dd HH:mm')
  } catch {
    return String(val)
  }
}

function statusClass(status) {
  const s = (status || '').toLowerCase()
  const base = 'text-xs font-medium px-2 py-0.5 rounded'
  if (s === 'success') return `${base} bg-green-100 text-green-800`
  if (s === 'failed') return `${base} bg-red-100 text-red-800`
  if (s === 'pending') return `${base} bg-blue-100 text-blue-800`
  if (s === 'merged' || s === 'silenced')
    return `${base} bg-gray-100 text-gray-700`
  return `${base} bg-gray-100 text-gray-600`
}

function onFiltersChanged() {
  page.value = 1
  debouncedFetch()
}

const debouncedFetch = useDebounceFn(() => {
  fetchRecords()
}, 300)

function resetFilters() {
  const range = getDefaultDetailDateRange()
  filters.value = {
    source_app: '',
    source_type: '',
    status: '',
    start_date: range.start_date,
    end_date: range.end_date
  }
  page.value = 1
  fetchRecords()
}

async function handlePageSizeChange() {
  page.value = 1
  await fetchRecords()
}

async function goToPreviousPage() {
  if (page.value <= 1) return
  page.value -= 1
  await fetchRecords()
}

async function goToNextPage() {
  if (page.value >= totalPages.value) return
  page.value += 1
  await fetchRecords()
}

function openDetail(uuid) {
  selectedRecordUuid.value = uuid
  detailVisible.value = true
  detailRecord.value = null
}

function closeDetail() {
  detailVisible.value = false
  selectedRecordUuid.value = null
  detailRecord.value = null
}

async function fetchDetail() {
  if (!selectedRecordUuid.value) return
  detailLoading.value = true
  detailRecord.value = null
  try {
    const data = await notificationsAdminApi.getRecord(selectedRecordUuid.value)
    detailRecord.value = data
  } catch {
    detailRecord.value = null
  } finally {
    detailLoading.value = false
  }
}

async function fetchRecords() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.value.source_app) params.source_app = filters.value.source_app
    if (filters.value.source_type)
      params.source_type = filters.value.source_type
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = await notificationsAdminApi.getRecords(params)
    records.value = data?.results ?? []
    total.value = data?.total ?? 0
  } catch (e) {
    showError(extractErrorMessage(e, t('common.error')))
    records.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRecords()
})

watch(detailVisible, (visible) => {
  if (visible && selectedRecordUuid.value) {
    fetchDetail()
  }
})
</script>
