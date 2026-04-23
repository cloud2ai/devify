<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('management.groupManagement') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('management.groupsSubtitle') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
            <span class="text-sm text-gray-600">{{
              t('management.totalGroups', { count: totalCount })
            }}</span>
            <div class="flex items-center gap-2">
              <BaseButton
                variant="outline"
                size="sm"
                :loading="loading"
                @click="fetchGroups"
              >
                {{ t('common.refresh') }}
              </BaseButton>
              <BaseButton
                variant="primary"
                size="sm"
                @click="showCreateModal = true"
              >
                {{ t('management.createGroup') }}
              </BaseButton>
            </div>
          </div>

          <BaseLoading v-if="loading && !groups.length" />

          <div
            v-else-if="error"
            class="py-16 text-center rounded-lg border border-gray-200 bg-gray-50"
          >
            <p class="text-sm font-medium text-red-600">{{ error }}</p>
          </div>

          <div
            v-else-if="!groups.length"
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
              <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    ID
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.groupName') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.groupUserCount') }}
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                  >
                    {{ t('management.permissionCount') }}
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-100">
                <tr
                  v-for="g in groups"
                  :key="g.id"
                  class="hover:bg-gray-50 transition-colors duration-150"
                >
                  <td class="px-4 py-4 text-sm text-gray-900">{{ g.id }}</td>
                  <td class="px-4 py-4 text-sm font-medium text-gray-900">
                    {{ g.name }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    {{ g.user_count ?? 0 }}
                  </td>
                  <td class="px-4 py-4 text-sm text-gray-500">
                    {{ g.permission_count ?? 0 }}
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
        :title="t('management.createGroup')"
        @close="closeCreateModal"
      >
        <form @submit.prevent="submitCreateGroup" class="space-y-4">
          <p v-if="createError" class="text-sm text-red-600">
            {{ createError }}
          </p>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{
              t('management.groupName')
            }}</label>
            <input
              v-model="createForm.name"
              type="text"
              class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              :placeholder="t('management.groupName')"
            />
          </div>
        </form>
        <template #footer>
          <div class="flex flex-row-reverse gap-2">
            <BaseButton
              variant="primary"
              :loading="createLoading"
              @click="submitCreateGroup"
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
const groups = ref([])
const loading = ref(false)
const error = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const showCreateModal = ref(false)
const createLoading = ref(false)
const createError = ref(null)
const createForm = ref({ name: '' })

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
  createError.value = null
  createForm.value = { name: '' }
}

async function handlePageSizeChange() {
  currentPage.value = 1
  await fetchGroups()
}

async function goToPreviousPage() {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  await fetchGroups()
}

async function goToNextPage() {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  await fetchGroups()
}

async function submitCreateGroup() {
  createError.value = null
  const name = (createForm.value.name || '').trim()
  if (!name) {
    createError.value = t('management.groupNameRequired')
    return
  }
  createLoading.value = true
  try {
    await managementApi.createGroup({ name })
    closeCreateModal()
    await fetchGroups()
  } catch (e) {
    if (e?.response?.data?.code === 'name_taken') {
      createError.value = t('management.groupNameTaken')
    } else {
      createError.value =
        e?.response?.data?.detail || e?.message || t('common.error')
    }
  } finally {
    createLoading.value = false
  }
}

async function fetchGroups() {
  loading.value = true
  error.value = null
  try {
    const data = await managementApi.getGroups({
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (Array.isArray(data)) {
      groups.value = data
      totalCount.value = data.length
    } else {
      groups.value = data?.results ?? []
      totalCount.value = Number(data?.count ?? groups.value.length)
    }
  } catch (e) {
    groups.value = []
    totalCount.value = 0
    error.value = e?.response?.data?.detail || e?.message || t('common.error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGroups()
})
</script>
