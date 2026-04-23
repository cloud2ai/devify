<template>
  <AppLayout>
    <div class="space-y-6">
      <VirtualEmailBanner
        :virtual-email="userStore.userInfo?.virtual_email"
        :label="t('settings.emailAddressDesc')"
      />

      <!-- Stats Cards -->
      <div class="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4">
        <BaseCard>
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div
                class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-white"
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
              </div>
            </div>
            <div class="ml-3 flex-1 min-w-0">
              <dl>
                <dt
                  class="text-xs sm:text-sm font-medium text-gray-500 truncate"
                >
                  {{ t('dashboard.stats.totalMessages') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.totalResults || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div
                class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-white"
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
              </div>
            </div>
            <div class="ml-3 flex-1 min-w-0">
              <dl>
                <dt
                  class="text-xs sm:text-sm font-medium text-gray-500 truncate"
                >
                  {{ t('dashboard.stats.thisWeek') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.thisWeek || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div
                class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
            <div class="ml-3 flex-1 min-w-0">
              <dl>
                <dt
                  class="text-xs sm:text-sm font-medium text-gray-500 truncate"
                >
                  {{ t('dashboard.stats.pending') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.pending || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div
                class="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center"
              >
                <svg
                  class="w-5 h-5 text-white"
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
              </div>
            </div>
            <div class="ml-3 flex-1 min-w-0">
              <dl>
                <dt
                  class="text-xs sm:text-sm font-medium text-gray-500 truncate"
                >
                  {{ t('dashboard.stats.completed') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.completed || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </BaseCard>
      </div>

      <!-- Chat Messages List -->
      <BaseCard :header-muted="true">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-2 text-gray-800">
              <svg
                class="w-5 h-5 -mt-px flex-none"
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
              <h3 class="text-base font-semibold leading-5">
                {{ t('dashboard.recentMessages') }}
              </h3>
            </div>
            <div class="flex items-center gap-2 flex-1 max-w-md">
              <div class="relative flex-1">
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="t('chats.searchPlaceholderDetailed')"
                  class="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                />
                <svg
                  class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400"
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
              </div>
              <BaseButton
                @click="refreshData"
                :loading="loading"
                variant="secondary"
                size="sm"
              >
                <template v-if="!loading">
                  <svg
                    class="w-4 h-4 mr-2"
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
                </template>
                {{ t('common.refresh') }}
              </BaseButton>
            </div>
          </div>
        </template>
        <div v-if="loading" class="text-center py-8">
          <div
            class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"
          ></div>
          <p class="mt-2 text-sm text-gray-500">{{ t('common.loading') }}</p>
        </div>

        <div v-else-if="results.length === 0" class="text-center py-8">
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">
            {{ searchQuery ? t('chats.noResults') : t('chats.noChats') }}
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            {{ searchQuery ? '' : t('chats.noChatsDesc') }}
          </p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="result in results"
            :key="result.id"
            class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
            @click="viewResult(result.uuid || result.id)"
          >
            <div
              class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3"
            >
              <div class="flex-1 min-w-0 space-y-2">
                <h4 class="text-sm font-medium text-gray-900 truncate">
                  {{
                    result.summary_title ||
                    result.subject ||
                    `Email #${result.id}`
                  }}
                </h4>
                <div class="text-sm text-gray-500 line-clamp-2 break-words">
                  {{ getPreviewText(result) }}
                </div>
                <div
                  class="flex flex-wrap items-center text-xs text-gray-400 gap-x-2 gap-y-1"
                >
                  <span class="whitespace-nowrap">{{
                    formatDateTime(result.received_at || result.created_at)
                  }}</span>
                  <span class="hidden sm:inline">•</span>
                  <span class="truncate max-w-40"
                    >{{ t('chats.from') }}: {{ getSender(result.sender) }}</span
                  >
                  <span class="hidden sm:inline">•</span>
                  <span class="whitespace-nowrap">{{
                    t('chats.attachments', {
                      count: result.attachments?.length || 0
                    })
                  }}</span>
                </div>
                <!-- Tags Display -->
                <div
                  v-if="
                    result.metadata?.keywords &&
                    result.metadata.keywords.length > 0
                  "
                  class="flex flex-wrap items-center gap-2 mt-2"
                >
                  <span
                    v-for="(tag, index) in getVisibleTags(
                      result.metadata.keywords
                    )"
                    :key="index"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {{ tag }}
                  </span>
                  <span
                    v-if="getRemainingTagsCount(result.metadata.keywords) > 0"
                    class="text-xs text-gray-500"
                  >
                    +{{ getRemainingTagsCount(result.metadata.keywords) }}
                  </span>
                </div>
              </div>
              <div
                class="flex items-center justify-between sm:justify-end sm:flex-col sm:items-end space-x-2 sm:space-x-0 sm:space-y-2 flex-shrink-0"
              >
                <div class="flex items-center gap-2">
                  <StatusBadge :status="result.status" />
                  <span
                    v-if="result.share_status?.is_active"
                    class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium"
                    :class="
                      result.share_status.is_expired
                        ? 'border-red-200 bg-red-50 text-red-600'
                        : 'border-green-200 bg-green-50 text-green-700'
                    "
                  >
                    <svg
                      class="w-3 h-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 8a3 3 0 11-6 0 3 3 0 016 0zM5.5 20a6.5 6.5 0 0113 0M4 4l16 16"
                      />
                    </svg>
                    {{ t('share.statusShared') }}
                  </span>
                </div>
                <svg
                  class="w-5 h-5 text-gray-400 flex-shrink-0"
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
              </div>
            </div>
          </div>
        </div>

        <!-- Load More Button -->
        <div v-if="pagination.hasMore && !loading" class="mt-6 text-center">
          <BaseButton
            @click="loadMoreData"
            :loading="loadingMore"
            variant="outline"
            size="md"
          >
            {{ t('common.loadMore') }}
          </BaseButton>
        </div>
      </BaseCard>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePreferencesStore } from '@/store/preferences'
import { useUserStore } from '@/store/user'
import { chatApi } from '@/api/chat'
import { formatDate } from '@/utils/timezone'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import VirtualEmailBanner from '@/components/ui/VirtualEmailBanner.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const { t } = useI18n()
const router = useRouter()
const preferencesStore = usePreferencesStore()
const userStore = useUserStore()

const loading = ref(false)
const loadingMore = ref(false)
const searchQuery = ref('')
const results = ref([])
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0,
  hasMore: false
})
const stats = ref({
  totalResults: 0,
  thisWeek: 0,
  pending: 0,
  completed: 0
})

// Debounce function for search
let searchTimeout = null
const performSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    loadData()
  }, 500)
}

// Watch search query changes
watch(searchQuery, () => {
  performSearch()
})

const loadData = async (isLoadMore = false) => {
  if (isLoadMore) {
    loadingMore.value = true
  } else {
    loading.value = true
    pagination.value.page = 1
    results.value = []
  }

  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim()
    }
    const response = await chatApi.getThreadlines(params)
    // Handle the actual response format from backend
    const responseData = response.data.data || response.data
    const newResults = responseData.list || responseData.results || []

    if (isLoadMore) {
      results.value = [...results.value, ...newResults]
    } else {
      results.value = newResults
    }

    // Update pagination info from backend
    if (responseData.pagination) {
      pagination.value = {
        page: responseData.pagination.page || pagination.value.page,
        pageSize: responseData.pagination.pageSize || pagination.value.pageSize,
        total: responseData.pagination.total || 0,
        hasMore:
          responseData.pagination.next !== null &&
          responseData.pagination.next !== undefined
      }
    }

    // Calculate stats (only on initial load, not on load more)
    if (!isLoadMore) {
      stats.value = {
        totalResults: pagination.value.total,
        thisWeek: results.value.filter((r) =>
          isThisWeek(r.received_at || r.created_at)
        ).length,
        pending: results.value.filter((r) => r.status === 'pending').length,
        completed: results.value.filter((r) => r.status === 'completed').length
      }
    }
  } catch (error) {
    // Error handling is done silently to avoid blocking UI
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMoreData = async () => {
  if (loadingMore.value || !pagination.value.hasMore) return

  pagination.value.page += 1
  await loadData(true)
}

const refreshData = () => {
  loadData()
}

const viewResult = (id) => {
  router.push(`/chats/${id}`)
}

const formatDateTime = (dateString) => {
  if (!dateString) return t('common.noData')

  // Use different date format based on language
  const dateFormat =
    preferencesStore.currentLanguage === 'zh-CN'
      ? 'yyyy年MM月dd日 HH:mm'
      : 'MMM dd, yyyy HH:mm'

  return formatDate(
    dateString,
    preferencesStore.currentTimezone,
    dateFormat,
    preferencesStore.currentLanguage
  )
}

const isThisWeek = (dateString) => {
  if (!dateString) return false
  const date = new Date(dateString)
  const now = new Date()
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  return date >= weekAgo
}

// Get concise plain-text preview (strip markdown for list view)
const getPreviewText = (result) => {
  // Helper to extract text from summary_content (may contain markdown)
  const extractPlainText = (content) => {
    if (!content) return ''
    if (typeof content !== 'string') return String(content)

    // Strip markdown formatting for list preview
    // Remove headers (# ## ###)
    content = content.replace(/^#{1,6}\s+/gm, '')
    // Remove bold/italic
    content = content.replace(/\*\*|\*\*/g, '')
    content = content.replace(/\*|\*/g, '')
    // Remove links [text](url)
    content = content.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
    // Remove images ![alt](url)
    content = content.replace(/!\[([^\]]*)\]\([^\)]+\)/g, '')
    // Remove code blocks
    content = content.replace(/```[\s\S]*?```/g, '')
    // Remove inline code
    content = content.replace(/`([^`]+)`/g, '$1')
    // Remove horizontal rules
    content = content.replace(/^---+$/gm, '')
    // Remove list markers
    content = content.replace(/^[\*\-\+]\s+/gm, '')
    content = content.replace(/^\d+\.\s+/gm, '')
    // Trim whitespace
    content = content.trim()

    return content
  }

  // Try summary_content first (may contain markdown)
  if (result.summary_content) {
    const text = extractPlainText(result.summary_content)
    if (text && text.length > 0) {
      return text.length > 150 ? text.substring(0, 150) + '...' : text
    }
  }

  // Fallback to other fields
  const prefer = [
    result.text_content,
    result.preview,
    result.summary_text,
    result.llm_content,
    result.body,
    result.description
  ]

  for (const item of prefer) {
    if (!item) continue
    if (typeof item === 'string' && item.trim()) {
      return item.length > 150 ? item.substring(0, 150) + '...' : item
    }
  }

  return t('chats.noSummary')
}

// Normalize sender display
const getSender = (sender) => {
  if (!sender) return t('common.noData')
  if (typeof sender === 'string') return sender
  if (typeof sender === 'object')
    return sender.name || sender.email || sender.address || t('common.noData')
  return ''
}

// Get visible tags based on screen width
const getVisibleTags = (tags) => {
  if (!tags || !Array.isArray(tags)) return []

  // Use window width to determine max tags
  const maxTags = window.innerWidth >= 768 ? 5 : 3
  return tags.slice(0, maxTags)
}

// Get remaining tags count
const getRemainingTagsCount = (tags) => {
  if (!tags || !Array.isArray(tags)) return 0

  const maxTags = window.innerWidth >= 768 ? 5 : 3
  return Math.max(0, tags.length - maxTags)
}

onMounted(async () => {
  // Refresh user info if missing virtual_email (important after OAuth setup completion)
  // Otherwise use existing user data from store
  if (!userStore.userInfo?.virtual_email) {
    await userStore.checkAuthStatus()
  }
  loadData()
})
</script>
