<template>
  <AdminLayout>
    <div class="w-full max-w-full space-y-6 p-6">
      <div>
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('dataManagement.conversations.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('dataManagement.conversations.subtitle') }}
        </p>
      </div>

      <div class="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div class="flex flex-col p-6">
          <div class="mb-4 flex items-center justify-end gap-3">
            <div
              class="flex min-w-0 flex-1 items-center justify-end gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              <BaseInput
                v-model="filters.search"
                :placeholder="
                  t('dataManagement.conversations.searchPlaceholder')
                "
                class="w-[26rem] max-w-full shrink-0"
                @update:modelValue="debouncedSearch"
              >
                <template #icon>
                  <svg
                    class="h-4 w-4 text-gray-400"
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
                class="flex shrink-0 items-center gap-1"
                @click="openFilterDrawer"
              >
                <svg
                  class="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 4h18M6 12h12M10 20h4"
                  />
                </svg>
                {{ t('dataManagement.conversations.filter') }}
              </BaseButton>

              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                :title="t('common.refresh')"
                class="flex shrink-0 items-center gap-1 shadow-sm transition-shadow hover:shadow-md"
                @click="fetchConversations"
              >
                <svg
                  v-if="!loading"
                  class="h-4 w-4"
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

          <div
            v-if="hasActiveFilters"
            class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3"
          >
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="text-xs font-semibold uppercase tracking-wider text-gray-500"
                >{{ t('dataManagement.conversations.activeFilters') }}</span
              >
              <span class="text-sm text-gray-600">{{
                t('dataManagement.conversations.activeFiltersHint')
              }}</span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span
                v-for="chip in activeFilterChips"
                :key="chip.key"
                class="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-sm text-gray-700 shadow-sm"
              >
                <span class="font-medium text-gray-500">{{ chip.label }}</span>
                <span class="max-w-[16rem] truncate">{{ chip.value }}</span>
                <button
                  type="button"
                  class="text-gray-400 hover:text-gray-700"
                  :aria-label="
                    t('dataManagement.conversations.removeFilter', {
                      label: chip.label
                    })
                  "
                  @click="chip.onRemove"
                >
                  <svg
                    class="h-4 w-4"
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
              </span>
              <BaseButton
                variant="outline"
                size="sm"
                class="shrink-0"
                @click="resetFilters"
                >{{
                  t('dataManagement.conversations.clearFilters')
                }}</BaseButton
              >
            </div>
          </div>

          <BaseLoading v-if="loading && conversations.length === 0" />

          <ConversationDetail
            v-if="detailVisible"
            v-model:detailTab="detailTab"
            :visible="detailVisible"
            :loading="detailLoading"
            :conversation="selectedConversation"
            :tabs="tabs"
            :conversation-todos="conversationTodos"
            :non-image-attachments="nonImageAttachments"
            :relay-deliveries="relayDeliveries"
            :related-tasks-loading="relatedTasksLoading"
            :related-tasks="relatedTasks"
            :selected-task-execution="selectedTaskExecution"
            :show-task-detail="showTaskDetail"
            :detail-steps="detailSteps"
            :current-progress-text="currentProgressText"
            :task-pagination-showing="taskPaginationShowing"
            :task-page="taskPage"
            :task-page-size="taskPageSize"
            :task-total-count="taskTotalCount"
            :task-total-pages="taskTotalPages"
            @close="closeDetail"
            @open-conversation="handleOpenConversation"
            @open-task="openTaskExecution"
            @close-task-detail="closeTaskDetail"
            @change-task-page-size="changeTaskPageSize"
            @previous-task-page="goToPreviousTaskPage"
            @next-task-page="goToNextTaskPage"
          />

          <div
            v-if="!loading && conversations.length === 0"
            class="rounded-lg border border-gray-200 bg-gray-50 py-16 text-center"
          >
            <svg
              class="mx-auto mb-4 h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 10h8M8 14h5m-9 4h14a2 2 0 002-2V8a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            <p class="text-sm font-medium text-gray-600">
              {{ t('dataManagement.conversations.noData') }}
            </p>
          </div>

          <ConversationTable
            v-else
            :items="conversations"
            :page="page"
            :page-size="pageSize"
            :pagination-showing="paginationShowing"
            :total-count="totalCount"
            :total-pages="totalPages"
            @row-click="openConversation"
            @relay-click="openConversationAtRelay"
            @change-page-size="handlePageSizeChange"
            @previous-page="goToPreviousPage"
            @next-page="goToNextPage"
          />
        </div>
      </div>

      <ConversationFilterDrawer
        :show="showFilterDrawer"
        :draft-filters="draftFilters"
        :user-options="userOptions"
        @close="closeFilterDrawer"
        @reset="resetDraftFilters"
        @confirm="confirmFilterDrawer"
      />
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/api'
import { dataManagementApi, managementApi } from '@/admin/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import ConversationDetail from './components/ConversationDetail.vue'
import ConversationFilterDrawer from './components/ConversationFilterDrawer.vue'
import ConversationTable from './components/ConversationTable.vue'

const { t } = useI18n()
const { showError } = useToast()

const loading = ref(false)
const conversations = ref([])
const totalCount = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(20)
const userOptions = ref([])
const filters = reactive({
  search: '',
  user_id: '',
  status: '',
  start_date: '',
  end_date: ''
})
const draftFilters = reactive({
  search: '',
  user_id: '',
  status: '',
  start_date: '',
  end_date: ''
})

const detailVisible = ref(false)
const detailLoading = ref(false)
const selectedConversation = ref(null)
const detailTab = ref('ai')
const showFilterDrawer = ref(false)
const relatedTasksLoading = ref(false)
const relatedTasks = ref([])
const selectedTaskExecution = ref(null)
const showTaskDetail = ref(false)
const taskPage = ref(1)
const taskPageSize = ref(20)
const taskTotalCount = ref(0)
const taskTotalPages = ref(1)

const tabs = computed(() => [
  {
    key: 'ai',
    label: t('dataManagement.conversations.tabAiInfo')
  },
  {
    key: 'relay',
    label: t('dataManagement.conversations.tabRelay')
  },
  {
    key: 'raw',
    label: t('dataManagement.conversations.tabRawInfo')
  },
  {
    key: 'attachments',
    label: t('dataManagement.conversations.tabAttachments')
  },
  {
    key: 'tasks',
    label: t('dataManagement.conversations.tabTaskManagement')
  }
])

const paginationShowing = computed(() => ({
  from: totalCount.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1,
  to: Math.min(page.value * pageSize.value, totalCount.value),
  total: totalCount.value
}))

const taskPaginationShowing = computed(() => ({
  from:
    taskTotalCount.value === 0
      ? 0
      : (taskPage.value - 1) * taskPageSize.value + 1,
  to: Math.min(taskPage.value * taskPageSize.value, taskTotalCount.value),
  total: taskTotalCount.value
}))

const activeFilterChips = computed(() => {
  const chips = []

  if (filters.search.trim()) {
    chips.push({
      key: 'search',
      label: t('dataManagement.conversations.searchLabel'),
      value: filters.search.trim(),
      onRemove: clearSearchFilter
    })
  }

  if (filters.user_id) {
    chips.push({
      key: 'user',
      label: t('dataManagement.conversations.userFilter'),
      value:
        userOptions.value.find((item) => item.id === filters.user_id)?.label ||
        filters.user_id,
      onRemove: clearUserFilter
    })
  }

  if (filters.status) {
    chips.push({
      key: 'status',
      label: t('dataManagement.conversations.statusFilter'),
      value: t(`common.status.${filters.status}`),
      onRemove: clearStatusFilter
    })
  }

  if (filters.start_date || filters.end_date) {
    const start = filters.start_date || '...'
    const end = filters.end_date || '...'
    chips.push({
      key: 'date',
      label: t('common.dateRange'),
      value: `${start} ${t('dataManagement.conversations.to')} ${end}`,
      onRemove: clearDateFilter
    })
  }

  return chips
})

const hasActiveFilters = computed(() => activeFilterChips.value.length > 0)

const conversationTodos = computed(() =>
  Array.isArray(selectedConversation.value?.todos)
    ? selectedConversation.value.todos
    : []
)

const nonImageAttachments = computed(() =>
  Array.isArray(selectedConversation.value?.attachments)
    ? selectedConversation.value.attachments.filter((item) => !item?.is_image)
    : []
)

const relayDeliveries = computed(() =>
  Array.isArray(selectedConversation.value?.relay_deliveries)
    ? selectedConversation.value.relay_deliveries
    : []
)

const currentProgressText = computed(() => {
  const meta = selectedTaskExecution.value?.metadata || {}
  const percent = meta.progress_percent
  const msg = meta.progress_message
  const step = meta.progress_step
  if (percent != null && (msg || step)) {
    const parts = []
    if (step) parts.push(step)
    if (msg) parts.push(msg)
    parts.push(`${percent}%`)
    return parts.join(' · ')
  }
  if (msg) return msg
  if (step) return step
  return ''
})

const detailSteps = computed(() => {
  const meta = selectedTaskExecution.value?.metadata || {}
  const buildStep = (item) => {
    const progressBits = []
    if (
      item.progress_current_step != null &&
      item.progress_total_steps != null
    ) {
      progressBits.push(
        `${item.progress_current_step}/${item.progress_total_steps}`
      )
    } else if (item.progress_percent != null) {
      progressBits.push(`${item.progress_percent}%`)
    }
    if (item.progress_message) {
      progressBits.push(item.progress_message)
    }

    const context =
      item.context && typeof item.context === 'object' ? item.context : {}
    const contextLabels = []
    const contextPairs = [
      ['email_id', t('dataManagement.conversations.emailIdShort')],
      ['user_id', t('dataManagement.conversations.userIdShort')],
      ['scene', t('dataManagement.conversations.sceneShort')],
      ['trigger_source', t('dataManagement.conversations.triggerSourceShort')],
      ['language', t('dataManagement.conversations.languageShort')]
    ]
    for (const [key, label] of contextPairs) {
      const value = item[key] ?? context[key]
      if (
        value !== undefined &&
        value !== null &&
        String(value).trim() !== ''
      ) {
        contextLabels.push(`${label}: ${value}`)
      }
    }

    return {
      title: item.progress_step ?? item.step ?? item.name ?? item.action ?? '',
      message:
        item.raw_message ??
        item.progress_message ??
        item.message ??
        item.description ??
        '',
      level: item.level,
      timestamp: item.timestamp ?? item.time,
      exception: item.exception,
      progressSummary: progressBits.join(' · '),
      contextLabels
    }
  }

  if (Array.isArray(meta.steps) && meta.steps.length > 0) {
    return meta.steps.map(buildStep)
  }
  if (Array.isArray(meta.logs) && meta.logs.length > 0) {
    return meta.logs.map(buildStep)
  }
  if (Array.isArray(meta.task_logs) && meta.task_logs.length > 0) {
    return meta.task_logs.map(buildStep)
  }
  return []
})

function formatUserLabel(user) {
  if (!user) return '-'
  if (user.first_name && user.last_name)
    return `${user.first_name} ${user.last_name}`
  if (user.first_name) return user.first_name
  if (user.last_name) return user.last_name
  return user.username || String(user.id ?? '-')
}

const userOptionsLoading = ref(false)
const userOptionsLoaded = ref(false)

async function fetchUserOptions() {
  if (userOptionsLoaded.value || userOptionsLoading.value) return
  userOptionsLoading.value = true
  try {
    const data = await managementApi.getUsers({
      page_size: 200
    })
    const list = Array.isArray(data)
      ? data
      : Array.isArray(data?.results)
        ? data.results
        : []
    userOptions.value = list.map((u) => ({
      id: String(u.id),
      label: formatUserLabel(u)
    }))
    userOptionsLoaded.value = true
  } catch {
    userOptions.value = []
  } finally {
    userOptionsLoading.value = false
  }
}

async function fetchConversations() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    if (filters.search.trim()) params.search = filters.search.trim()
    if (filters.user_id) params.user_id = filters.user_id
    if (filters.status) params.status = filters.status
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date

    const data = await dataManagementApi.getConversations(params)
    const list =
      data?.results ?? data?.list ?? (Array.isArray(data) ? data : [])
    const count = Number(data?.count ?? data?.pagination?.total ?? list.length)
    conversations.value = list
    totalCount.value = Number.isFinite(count) ? count : list.length
    totalPages.value =
      totalCount.value > 0 ? Math.ceil(totalCount.value / pageSize.value) : 1
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
    conversations.value = []
    totalCount.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  fetchConversations()
}

function syncDraftFiltersFromApplied() {
  draftFilters.search = filters.search
  draftFilters.user_id = filters.user_id
  draftFilters.status = filters.status
  draftFilters.start_date = filters.start_date
  draftFilters.end_date = filters.end_date
}

function openFilterDrawer() {
  syncDraftFiltersFromApplied()
  showFilterDrawer.value = true
}

function closeFilterDrawer() {
  showFilterDrawer.value = false
}

async function confirmFilterDrawer() {
  filters.user_id = draftFilters.user_id
  filters.status = draftFilters.status
  filters.start_date = draftFilters.start_date
  filters.end_date = draftFilters.end_date
  showFilterDrawer.value = false
  page.value = 1
  await fetchConversations()
}

function clearSearchFilter() {
  filters.search = ''
  applyFilters()
}

function clearUserFilter() {
  filters.user_id = ''
  applyFilters()
}

function clearStatusFilter() {
  filters.status = ''
  applyFilters()
}

function clearDateFilter() {
  filters.start_date = ''
  filters.end_date = ''
  applyFilters()
}

function resetDraftFilters() {
  draftFilters.search = ''
  draftFilters.user_id = ''
  draftFilters.status = ''
  draftFilters.start_date = ''
  draftFilters.end_date = ''
}

const debouncedSearch = useDebounceFn(() => {
  page.value = 1
  fetchConversations()
}, 300)

async function resetFilters() {
  filters.search = ''
  filters.user_id = ''
  filters.status = ''
  filters.start_date = ''
  filters.end_date = ''
  syncDraftFiltersFromApplied()
  page.value = 1
  showFilterDrawer.value = false
  await fetchConversations()
}

async function handlePageSizeChange(newSize) {
  pageSize.value = newSize
  page.value = 1
  await fetchConversations()
}

async function goToPreviousPage() {
  if (page.value <= 1) return
  page.value -= 1
  await fetchConversations()
}

async function goToNextPage() {
  if (page.value >= totalPages.value) return
  page.value += 1
  await fetchConversations()
}

async function openConversation(item, initialTab = 'ai') {
  return openConversationByUuid(item.uuid, initialTab)
}

function openConversationAtRelay(item) {
  return openConversation(item, 'relay')
}

async function openConversationByUuid(uuid, initialTab = 'ai') {
  detailVisible.value = true
  detailLoading.value = true
  detailTab.value = initialTab
  selectedConversation.value = null
  relatedTasks.value = []
  selectedTaskExecution.value = null
  showTaskDetail.value = false
  taskPage.value = 1
  taskTotalCount.value = 0
  taskTotalPages.value = 1

  try {
    const data = await dataManagementApi.getConversation(uuid)
    selectedConversation.value = data
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
    closeDetail()
  } finally {
    detailLoading.value = false
  }
}

function handleOpenConversation(payload) {
  if (!payload || !payload.uuid) return
  return openConversationByUuid(payload.uuid, payload.initialTab || 'ai')
}

function closeDetail() {
  detailVisible.value = false
  selectedConversation.value = null
  selectedTaskExecution.value = null
  showTaskDetail.value = false
  relatedTasks.value = []
  taskPage.value = 1
  taskTotalCount.value = 0
  taskTotalPages.value = 1
}

async function fetchRelatedTasks() {
  if (!selectedConversation.value) return
  relatedTasksLoading.value = true
  try {
    const data = await dataManagementApi.getConversationTasks(
      selectedConversation.value.uuid,
      {
        page: taskPage.value,
        page_size: taskPageSize.value
      }
    )
    const list =
      data?.results ?? data?.list ?? (Array.isArray(data) ? data : [])
    const count = Number(data?.count ?? data?.pagination?.total ?? list.length)
    relatedTasks.value = list
    taskTotalCount.value = Number.isFinite(count) ? count : list.length
    taskTotalPages.value =
      taskTotalCount.value > 0
        ? Math.ceil(taskTotalCount.value / taskPageSize.value)
        : 1
    if (
      selectedTaskExecution.value &&
      !list.some((task) => task.id === selectedTaskExecution.value.id)
    ) {
      selectedTaskExecution.value = null
      showTaskDetail.value = false
    }
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
    relatedTasks.value = []
    taskTotalCount.value = 0
    taskTotalPages.value = 1
    selectedTaskExecution.value = null
  } finally {
    relatedTasksLoading.value = false
  }
}

async function openTaskExecution(task, options = {}) {
  if (!task?.id || !selectedConversation.value?.uuid) return
  try {
    const data = await dataManagementApi.getConversationTask(
      selectedConversation.value.uuid,
      task.id
    )
    selectedTaskExecution.value = data
    if (!options.silent) {
      showTaskDetail.value = true
      detailTab.value = 'tasks'
    }
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
  }
}

function closeTaskDetail() {
  showTaskDetail.value = false
}

async function changeTaskPageSize(newSize) {
  taskPageSize.value = newSize
  taskPage.value = 1
  await fetchRelatedTasks()
}

async function goToPreviousTaskPage() {
  if (taskPage.value <= 1) return
  taskPage.value -= 1
  await fetchRelatedTasks()
}

async function goToNextTaskPage() {
  if (taskPage.value >= taskTotalPages.value) return
  taskPage.value += 1
  await fetchRelatedTasks()
}

watch(
  () => detailTab.value,
  (tab) => {
    if (tab === 'tasks' && detailVisible.value && selectedConversation.value) {
      fetchRelatedTasks()
    }
  }
)

onMounted(() => {
  fetchUserOptions()
  fetchConversations()
})
</script>
