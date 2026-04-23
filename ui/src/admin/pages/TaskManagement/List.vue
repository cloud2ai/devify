<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('taskManagement.list.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('taskManagement.list.subtitle') }}
        </p>
      </div>

      <div class="bg-white rounded border border-gray-200 shadow-sm">
        <div class="p-6">
          <!-- Toolbar -->
          <div
            class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6"
          >
            <div class="flex items-center gap-3 flex-wrap">
              <label
                class="text-sm font-medium text-gray-700 whitespace-nowrap"
              >
                {{ t('taskManagement.list.taskTypeFilter') }}
              </label>
              <select
                v-model="filterModule"
                class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 min-w-[10rem]"
                @change="onFilterChange"
              >
                <option value="">
                  {{ t('taskManagement.list.taskTypeAll') }}
                </option>
                <option value="billing">
                  {{ t('taskManagement.list.taskTypeBilling') }}
                </option>
                <option value="agentcore_notifier">
                  {{ t('taskManagement.list.taskTypeNotifier') }}
                </option>
                <option value="agentcore_task">
                  {{ t('taskManagement.list.taskTypeTask') }}
                </option>
                <option value="threadline">
                  {{ t('taskManagement.list.taskTypeThreadline') }}
                </option>
              </select>
              <label
                class="text-sm font-medium text-gray-700 whitespace-nowrap"
              >
                {{ t('taskManagement.list.userFilter') }}
              </label>
              <select
                v-model="filterUserId"
                class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 min-w-[10rem]"
                @change="onFilterChange"
              >
                <option value="">
                  {{ t('taskManagement.list.userFilterAll') }}
                </option>
                <option v-for="u in userOptions" :key="u.id" :value="u.id">
                  {{ u.label }}
                </option>
              </select>
              <span class="text-sm text-gray-600 whitespace-nowrap">{{
                t('taskManagement.list.dateRange')
              }}</span>
              <input
                v-model="filterStartDate"
                type="date"
                :max="filterEndDate || undefined"
                class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                @change="onFilterChange"
              />
              <span class="text-gray-400">–</span>
              <input
                v-model="filterEndDate"
                type="date"
                :min="filterStartDate || undefined"
                class="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                @change="onFilterChange"
              />
            </div>

            <div class="flex items-center gap-3 w-full sm:w-auto">
              <BaseInput
                v-model="searchQuery"
                :placeholder="t('taskManagement.list.searchPlaceholder')"
                class="flex-1 sm:w-64"
                @update:modelValue="debouncedLoad"
              >
                <template #icon>
                  <svg
                    class="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </template>
              </BaseInput>

              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                @click="loadTasks"
                :title="t('common.refresh')"
                class="flex items-center gap-1 shadow-sm hover:shadow-md transition-shadow"
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
          </div>

          <BaseLoading v-if="loading && tasks.length === 0" />

          <div
            v-else-if="!loading && tasks.length === 0"
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
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            <p class="text-sm font-medium text-gray-600">
              {{ t('taskManagement.list.noTasks') }}
            </p>
          </div>

          <!-- Desktop Table View -->
          <div
            v-else
            class="overflow-x-auto relative rounded-lg border border-gray-200 bg-white shadow-sm"
          >
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.taskName') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.module') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.status') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.startedAt') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.duration') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('taskManagement.list.createdBy') }}
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-100">
                <tr
                  v-for="task in tasks"
                  :key="task.id"
                  @click="handlePreview(task)"
                  class="cursor-pointer transition-colors duration-150 hover:bg-gray-50"
                >
                  <td
                    class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900"
                  >
                    {{ task.task_name || '-' }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {{ task.module || '-' }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <StatusBadge :status="mapStatus(task.status)" />
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDate(task.started_at) }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDuration(task.duration) }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {{ task.created_by_username || '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-if="totalCount > 0"
            class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 pt-4"
          >
            <p class="text-sm text-gray-600">
              {{ t('common.pagination.showing', paginationShowing) }}
            </p>
            <div class="flex items-center gap-2">
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
                :disabled="currentPage <= 1"
                @click="goToPreviousPage"
              >
                {{ t('common.pagination.previous') }}
              </BaseButton>
              <BaseButton
                variant="outline"
                size="sm"
                :disabled="currentPage >= totalPages"
                @click="goToNextPage"
              >
                {{ t('common.pagination.next') }}
              </BaseButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Task Detail Panel -->
      <TaskExecutionDetailPanel
        :show="showPreviewModal"
        :task="selectedTask"
        @close="showPreviewModal = false"
      />
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { format } from 'date-fns'
import { useDebounceFn } from '@vueuse/core'
import { useToast } from '@/composables/useToast'
import { extractResponseData, extractErrorMessage } from '@/utils/api'
import { formatDuration } from '@/utils/formatting'
import { taskManagementApi, managementApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TaskExecutionDetailPanel from '@/components/task-management/TaskExecutionDetailPanel.vue'

const { t } = useI18n()
const { showError } = useToast()

function getDefaultDetailDateRange() {
  const now = new Date()
  const endStr = format(now, 'yyyy-MM-dd')
  const start = new Date(now)
  start.setDate(start.getDate() - 3)
  return { startDate: format(start, 'yyyy-MM-dd'), endDate: endStr }
}

function toDateBoundaryIso(dateStr, boundary = 'start') {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-').map(Number)
  if (!year || !month || !day) return dateStr
  const hours = boundary === 'end' ? 23 : 0
  const minutes = boundary === 'end' ? 59 : 0
  const seconds = boundary === 'end' ? 59 : 0
  const milliseconds = boundary === 'end' ? 999 : 0
  return new Date(
    year,
    month - 1,
    day,
    hours,
    minutes,
    seconds,
    milliseconds
  ).toISOString()
}

const defaultDateRange = getDefaultDetailDateRange()
const loading = ref(false)
const tasks = ref([])
const searchQuery = ref('')
const filterModule = ref('')
const filterUserId = ref('')
const filterStartDate = ref(defaultDateRange.startDate)
const filterEndDate = ref(defaultDateRange.endDate)
const userOptions = ref([])
const showPreviewModal = ref(false)
const selectedTask = ref(null)
const currentPage = ref(1)
const totalCount = ref(0)
const totalPages = ref(1)
const pageSize = ref(20)

const paginationShowing = computed(() => ({
  from: (currentPage.value - 1) * pageSize.value + 1,
  to: Math.min(currentPage.value * pageSize.value, totalCount.value),
  total: totalCount.value
}))

function mapStatus(status) {
  const m = {
    PENDING: 'pending',
    STARTED: 'processing',
    SUCCESS: 'success',
    FAILURE: 'failed',
    RETRY: 'processing',
    REVOKED: 'failed'
  }
  return m[status] || (status && status.toLowerCase()) || 'pending'
}

function formatDate(val) {
  if (!val) return '-'
  try {
    return format(new Date(val), 'yyyy-MM-dd HH:mm')
  } catch {
    return val
  }
}

async function loadTasks() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      my_tasks: 'false'
    }
    if (filterModule.value) {
      params.module = filterModule.value
    }
    if (filterUserId.value) {
      params.created_by = filterUserId.value
    }
    if (filterStartDate.value) {
      params.start_date = toDateBoundaryIso(filterStartDate.value, 'start')
    }
    if (filterEndDate.value) {
      params.end_date = toDateBoundaryIso(filterEndDate.value, 'end')
    }
    if (searchQuery.value.trim()) {
      params.task_name = searchQuery.value.trim()
    }
    const res = await taskManagementApi.getExecutions(params)
    const data = extractResponseData(res)
    const list =
      data?.results ?? data?.list ?? (Array.isArray(data) ? data : [])
    const serverTotal = data?.count ?? data?.pagination?.total
    const hasServerPagination = Number.isFinite(Number(serverTotal))
    const total = hasServerPagination ? Number(serverTotal) : list.length
    tasks.value = hasServerPagination
      ? list
      : list.slice(
          (currentPage.value - 1) * pageSize.value,
          currentPage.value * pageSize.value
        )
    totalCount.value = total
    totalPages.value = total > 0 ? Math.ceil(total / pageSize.value) : 1
  } catch (e) {
    showError(extractErrorMessage(e, t('common.error')))
    tasks.value = []
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  currentPage.value = 1
  loadTasks()
}

async function handlePageSizeChange() {
  currentPage.value = 1
  await loadTasks()
}

async function goToPreviousPage() {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  await loadTasks()
}

async function goToNextPage() {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  await loadTasks()
}

function toUserLabel(u) {
  if (u.display_name) return u.display_name
  if (u.username) return u.username
  if (u.id != null) return String(u.id)
  return ''
}

async function fetchUserOptions() {
  try {
    const data = await managementApi.getUsers({ page_size: 200 })
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

const debouncedLoad = useDebounceFn(() => {
  currentPage.value = 1
  loadTasks()
}, 300)

async function handlePreview(task) {
  try {
    const res = await taskManagementApi.getExecution(task.id)
    selectedTask.value = extractResponseData(res)
    showPreviewModal.value = true
  } catch (e) {
    showError(extractErrorMessage(e, t('common.error')))
  }
}

onMounted(() => {
  fetchUserOptions()
  loadTasks()
})
</script>
