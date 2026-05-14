<template>
  <div>
    <div class="overflow-x-auto rounded-lg border border-gray-200">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gradient-to-r from-gray-50 to-gray-100">
          <tr>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('dataManagement.conversations.subject') }}
            </th>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('taskManagement.list.createdBy') }}
            </th>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('dataManagement.conversations.relay') }}
            </th>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('dataManagement.conversations.mergeRelation') }}
            </th>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('taskManagement.list.status') }}
            </th>
            <th
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700"
            >
              {{ t('dataManagement.conversations.receivedAt') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 bg-white">
          <tr
            v-for="item in items"
            :key="item.uuid"
            class="cursor-pointer transition-colors duration-150 hover:bg-gray-50"
            @click="$emit('row-click', item)"
          >
            <td class="px-4 py-4">
              <div class="space-y-1">
                <div class="text-sm font-medium text-gray-900">
                  {{ getConversationDisplayTitle(item) }}
                </div>
                <div class="line-clamp-2 text-xs text-gray-500">
                  {{ item.summary_content || item.text_content || '-' }}
                </div>
                <div class="break-all font-mono text-xs text-gray-400">
                  {{ item.message_id || item.uuid }}
                </div>
              </div>
            </td>
            <td class="whitespace-nowrap px-4 py-4">
              <div class="text-sm font-medium text-gray-900">
                {{ formatUserLabel(item.user) }}
              </div>
              <div class="text-xs text-gray-500">
                {{ item.user?.email || '-' }}
              </div>
            </td>
            <td class="whitespace-nowrap px-4 py-4">
              <button
                type="button"
                class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition-colors"
                :class="
                  item.relay_delivery_count
                    ? 'bg-blue-50 text-blue-700 ring-blue-200 hover:bg-blue-100'
                    : 'bg-gray-100 text-gray-500 ring-gray-200 hover:bg-gray-200'
                "
                :title="t('dataManagement.conversations.tabRelay')"
                @click.stop="$emit('relay-click', item)"
              >
                {{
                  item.relay_delivery_count
                    ? t('dataManagement.conversations.relayCount', {
                        count: item.relay_delivery_count
                      })
                    : t('dataManagement.conversations.relayNone')
                }}
              </button>
            </td>
            <td class="whitespace-nowrap px-4 py-4">
              <MergeStateBadge
                :state="item.is_canonical ? 'canonical' : 'original'"
                size="sm"
              />
            </td>
            <td class="whitespace-nowrap px-4 py-4">
              <StatusBadge :status="mapConversationStatus(item.status)" />
            </td>
            <td class="whitespace-nowrap px-4 py-4 text-sm text-gray-600">
              {{ formatDate(item.received_at) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-4 flex items-center justify-between gap-2">
      <span class="text-sm text-gray-600">
        {{
          t('dataManagement.conversations.listSummary', {
            count: totalCount
          })
        }}
      </span>
    </div>

    <div
      v-if="totalCount > pageSize"
      class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 pt-4"
    >
      <p class="text-sm text-gray-600">
        {{ t('common.pagination.showing', paginationShowing) }}
      </p>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600">
          {{ t('common.pagination.itemsPerPage') }}
        </label>
        <select
          :value="pageSize"
          class="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
          @change="$emit('change-page-size', Number($event.target.value))"
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
          @click="$emit('previous-page')"
        >
          {{ t('common.pagination.previous') }}
        </BaseButton>
        <BaseButton
          variant="outline"
          size="sm"
          :disabled="page >= totalPages"
          @click="$emit('next-page')"
        >
          {{ t('common.pagination.next') }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/ui/BaseButton.vue'
import MergeStateBadge from '@/components/ui/MergeStateBadge.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

defineProps({
  items: {
    type: Array,
    default: () => []
  },
  page: {
    type: Number,
    required: true
  },
  pageSize: {
    type: Number,
    required: true
  },
  paginationShowing: {
    type: Object,
    required: true
  },
  totalCount: {
    type: Number,
    required: true
  },
  totalPages: {
    type: Number,
    required: true
  }
})

defineEmits([
  'row-click',
  'relay-click',
  'change-page-size',
  'previous-page',
  'next-page'
])

const { t } = useI18n()

function formatDate(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

function formatUserLabel(user) {
  if (!user) return '-'
  if (user.first_name && user.last_name)
    return `${user.first_name} ${user.last_name}`
  if (user.first_name) return user.first_name
  if (user.last_name) return user.last_name
  return user.username || String(user.id ?? '-')
}

function getConversationDisplayTitle(conversation) {
  if (!conversation) return '-'
  return (
    conversation.summary_title ||
    conversation.subject ||
    conversation.text_content ||
    '-'
  )
}

function mapConversationStatus(status) {
  const normalized = String(status || '').toLowerCase()
  const map = {
    fetched: 'pending',
    processing: 'processing',
    success: 'success',
    failed: 'failed'
  }
  return map[normalized] || normalized || 'pending'
}
</script>
