<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('management.userManagement') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('management.usersSubtitle') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
            <span class="text-sm text-gray-600">{{
              t('management.totalUsers', { count: totalCount })
            }}</span>
            <div class="flex items-center gap-2">
              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                @click="fetchUsers"
              >
                {{ t('common.refresh') }}
              </BaseButton>
              <BaseButton variant="primary" size="sm" @click="openCreateModal">
                {{ t('management.createUser') }}
              </BaseButton>
            </div>
          </div>

          <BaseLoading v-if="loading && !users.length" />

          <div
            v-else-if="error"
            class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
          >
            <p class="text-sm font-medium text-red-600">{{ error }}</p>
          </div>

          <div
            v-else-if="!users.length"
            class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
          >
            <p class="text-sm font-medium text-gray-600">
              {{ t('common.noData') }}
            </p>
          </div>

          <div
            v-else
            class="overflow-x-auto relative rounded-lg border border-gray-200 bg-white shadow-sm"
          >
            <table class="min-w-full divide-y divide-gray-200">
              <colgroup>
                <col class="w-16" />
                <col class="w-40" />
                <col class="w-40" />
                <col class="w-56" />
                <col class="w-20" />
                <col class="w-20" />
                <col class="w-28" />
                <col class="w-36" />
                <col class="w-48" />
                <col class="w-48" />
              </colgroup>
              <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.id') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.username') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.displayName') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.email') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.isStaff') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.isActive') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.language') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.timezone') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.groups') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.dateJoined') }}
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-100">
                <tr
                  v-for="u in users"
                  :key="u.id"
                  class="hover:bg-gray-50 transition-colors duration-150"
                >
                  <td class="px-4 py-4 text-sm text-gray-900">{{ u.id }}</td>
                  <td class="px-4 py-4 text-sm font-medium text-gray-900">
                    {{ u.username }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    {{ u.display_name || '—' }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    {{ u.email || '—' }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    <span
                      class="inline-flex items-center justify-center rounded-full p-1.5"
                      :class="
                        u.is_staff
                          ? 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-200'
                          : 'bg-gray-100 text-gray-600 ring-1 ring-inset ring-gray-200'
                      "
                      :title="
                        u.is_staff
                          ? t('management.staffStatusAdmin')
                          : t('management.staffStatusUser')
                      "
                      :aria-label="
                        u.is_staff
                          ? t('management.staffStatusAdmin')
                          : t('management.staffStatusUser')
                      "
                    >
                      <svg
                        v-if="u.is_staff"
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path
                          d="M12 3l7 4v5c0 5-3.5 8.5-7 9-3.5-.5-7-4-7-9V7l7-4z"
                        />
                        <path d="M9 12l2 2 4-4" />
                      </svg>
                      <svg
                        v-else
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M12 12a4 4 0 100-8 4 4 0 000 8z" />
                        <path d="M4 20a8 8 0 0116 0" />
                      </svg>
                    </span>
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    <span
                      class="inline-flex items-center justify-center rounded-full p-1.5"
                      :class="
                        u.is_active !== false
                          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200'
                          : 'bg-gray-100 text-gray-600 ring-1 ring-inset ring-gray-200'
                      "
                      :title="
                        u.is_active !== false
                          ? t('management.activeStatusEnabled')
                          : t('management.activeStatusDisabled')
                      "
                      :aria-label="
                        u.is_active !== false
                          ? t('management.activeStatusEnabled')
                          : t('management.activeStatusDisabled')
                      "
                    >
                      <svg
                        v-if="u.is_active !== false"
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M12 2a10 10 0 100 20 10 10 0 000-20z" />
                        <path d="M8 12l2.5 2.5L16 9" />
                      </svg>
                      <svg
                        v-else
                        class="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M12 2a10 10 0 100 20 10 10 0 000-20z" />
                        <path d="M9 9l6 6M15 9l-6 6" />
                      </svg>
                    </span>
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap"
                      :class="
                        u.language
                          ? 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200'
                          : 'bg-gray-100 text-gray-500 ring-1 ring-inset ring-gray-200'
                      "
                    >
                      {{ u.language || '—' }}
                    </span>
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-mono whitespace-nowrap"
                      :class="
                        u.timezone
                          ? 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200'
                          : 'bg-gray-100 text-gray-500 ring-1 ring-inset ring-gray-200'
                      "
                    >
                      {{ u.timezone || '—' }}
                    </span>
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    {{
                      u.groups && u.groups.length
                        ? u.groups.map((g) => g.name).join(', ')
                        : '—'
                    }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    <span class="whitespace-nowrap text-sm text-gray-500">
                      {{ formatDate(u.date_joined) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-if="!loading && totalCount > 0"
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

      <BaseModal
        :show="showCreateModal"
        :title="t('management.createUser')"
        @close="closeCreateModal"
      >
        <form @submit.prevent="submitCreateUser" class="space-y-4">
          <p v-if="createError" class="text-sm text-red-600">
            {{ createError }}
          </p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.username')
            }}</label>
            <input
              v-model="createForm.username"
              type="text"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              :placeholder="t('management.username')"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.email')
            }}</label>
            <input
              v-model="createForm.email"
              type="email"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              :placeholder="t('management.email')"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('password.reset.newPassword')
            }}</label>
            <div class="relative">
              <input
                v-model="createForm.password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full rounded-md border border-gray-300 px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                :placeholder="t('password.reset.newPasswordPlaceholder')"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-500"
                :aria-label="
                  showPassword
                    ? t('common.hidePassword')
                    : t('common.showPassword')
                "
                @click="showPassword = !showPassword"
              >
                <svg
                  v-if="showPassword"
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                  />
                </svg>
                <svg
                  v-else
                  class="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
              </button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.language')
            }}</label>
            <select
              v-model="createForm.language"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 bg-white"
            >
              <option value="zh-CN">简体中文</option>
              <option value="en-US">English</option>
              <option value="ja-JP">日本語</option>
              <option value="ko-KR">한국어</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.timezone')
            }}</label>
            <select
              v-model="createForm.timezone"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 bg-white"
            >
              <option value="Asia/Shanghai">Asia/Shanghai</option>
              <option value="UTC">UTC</option>
              <option value="America/New_York">America/New_York</option>
              <option value="Europe/London">Europe/London</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.selectGroups')
            }}</label>
            <div
              class="max-h-32 overflow-y-auto rounded-md border border-gray-300 bg-white p-2 space-y-2"
            >
              <label
                v-for="g in groupOptions"
                :key="g.id"
                class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 rounded px-2 py-1"
              >
                <input
                  v-model="createForm.group_ids"
                  type="checkbox"
                  :value="g.id"
                  class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span class="text-sm text-gray-700">{{ g.name }}</span>
              </label>
              <p v-if="!groupOptions.length" class="text-sm text-gray-500 py-1">
                {{ t('common.noData') }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-3 py-1">
            <input
              v-model="createForm.is_staff"
              type="checkbox"
              id="create-user-is-staff"
              class="h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <label
              for="create-user-is-staff"
              class="text-sm font-medium text-gray-700 cursor-pointer"
            >
              {{ t('management.setAsAdmin') }}
            </label>
          </div>
        </form>
        <template #footer>
          <div class="flex flex-row-reverse gap-2">
            <BaseButton
              variant="primary"
              :loading="createLoading"
              @click="submitCreateUser"
            >
              {{ t('common.confirm') }}
            </BaseButton>
            <BaseButton variant="outline" @click="closeCreateModal">
              {{ t('common.cancel') }}
            </BaseButton>
          </div>
        </template>
      </BaseModal>
    </div>
  </AdminLayout>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { managementApi } from '@/admin/api'

const { t } = useI18n()
const users = ref([])
const loading = ref(false)
const error = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const showCreateModal = ref(false)
const createLoading = ref(false)
const createError = ref(null)
const showPassword = ref(false)
const groupOptions = ref([])
const createForm = ref({
  username: '',
  email: '',
  password: '',
  is_staff: false,
  group_ids: [],
  language: 'zh-CN',
  timezone: 'Asia/Shanghai'
})

const totalPages = computed(() =>
  totalCount.value > 0 ? Math.ceil(totalCount.value / pageSize.value) : 1
)

const paginationShowing = computed(() => ({
  from:
    totalCount.value === 0 ? 0 : (currentPage.value - 1) * pageSize.value + 1,
  to: Math.min(currentPage.value * pageSize.value, totalCount.value),
  total: totalCount.value
}))

function closeCreateModal() {
  showCreateModal.value = false
  showPassword.value = false
  createError.value = null
  createForm.value = {
    username: '',
    email: '',
    password: '',
    is_staff: false,
    group_ids: [],
    language: 'zh-CN',
    timezone: 'Asia/Shanghai'
  }
}

async function openCreateModal() {
  showCreateModal.value = true
  await loadGroupOptions()
}

async function loadGroupOptions() {
  try {
    const data = await managementApi.getGroups({ page: 1, page_size: 1000 })
    groupOptions.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    groupOptions.value = []
  }
}

async function submitCreateUser() {
  createError.value = null
  const username = (createForm.value.username || '').trim()
  const password = (createForm.value.password || '').trim()
  if (!username) {
    createError.value = t('management.usernameRequired')
    return
  }
  if (!password) {
    createError.value = t('management.passwordRequired')
    return
  }
  createLoading.value = true
  try {
    await managementApi.createUser({
      username,
      email: (createForm.value.email || '').trim(),
      password,
      is_staff: createForm.value.is_staff,
      group_ids: Array.isArray(createForm.value.group_ids)
        ? createForm.value.group_ids
        : [],
      language: (createForm.value.language || '').trim() || 'zh-CN',
      timezone: (createForm.value.timezone || '').trim() || 'Asia/Shanghai'
    })
    closeCreateModal()
    await fetchUsers()
  } catch (e) {
    const detail = e?.response?.data?.detail
    if (e?.response?.data?.code === 'username_taken') {
      createError.value = t('management.usernameTaken')
    } else if (e?.response?.data?.code === 'email_taken') {
      createError.value = t('management.emailTaken')
    } else {
      createError.value =
        typeof detail === 'string' ? detail : t('common.error')
    }
  } finally {
    createLoading.value = false
  }
}

function formatDate(value) {
  if (!value) return '—'
  try {
    const d = new Date(value)
    return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
  } catch {
    return value
  }
}

async function handlePageSizeChange() {
  currentPage.value = 1
  await fetchUsers()
}

async function goToPreviousPage() {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  await fetchUsers()
}

async function goToNextPage() {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  await fetchUsers()
}

async function fetchUsers() {
  loading.value = true
  error.value = null
  try {
    const data = await managementApi.getUsers({
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (Array.isArray(data)) {
      users.value = data
      totalCount.value = data.length
    } else {
      users.value = data?.results ?? []
      totalCount.value = Number(data?.count ?? users.value.length)
    }
  } catch (e) {
    users.value = []
    totalCount.value = 0
    error.value = e?.response?.data?.detail || e?.message || t('common.error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
