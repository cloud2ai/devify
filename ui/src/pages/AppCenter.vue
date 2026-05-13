<template>
  <AppLayout>
    <div class="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">
          {{ t('apps.centerTitle') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('apps.centerSubtitle') }}
        </p>
      </div>

      <BaseLoading v-if="loading" />

      <div v-else class="grid gap-4 md:grid-cols-2">
        <button
          v-for="app in appList"
          :key="app.key"
          type="button"
          class="rounded-2xl border border-gray-200 bg-white p-5 text-left shadow-sm transition hover:border-primary-300 hover:shadow-md"
          @click="openApp(app)"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="text-lg font-semibold text-gray-900">
                {{ app.name_zh || app.name }}
              </div>
              <div class="mt-1 text-sm text-gray-500">
                {{ app.name }}
              </div>
            </div>
            <span
              class="rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700"
            >
              {{ t('apps.openApp') }}
            </span>
          </div>
          <p class="mt-3 text-sm leading-6 text-gray-600">
            {{ app.description }}
          </p>
        </button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AppLayout from '@/components/layout/AppLayout.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { relayApi } from '@/api/relay'
import { extractErrorMessage } from '@/utils/api'
import { useToast } from '@/composables/useToast'

const { t } = useI18n()
const router = useRouter()
const { showError } = useToast()

const loading = ref(false)
const appList = ref([
  {
    key: 'relay',
    name: 'Relay',
    name_zh: '智能投递',
    path: '/apps/relay',
    description: t('apps.relayDesc')
  }
])

async function loadApps() {
  loading.value = true
  try {
    const data = await relayApi.getApps()
    if (Array.isArray(data) && data.length > 0) {
      appList.value = data
    }
  } catch (error) {
    showError(extractErrorMessage(error, t('common.error')))
  } finally {
    loading.value = false
  }
}

function openApp(app) {
  if (app?.path) {
    router.push(app.path)
  }
}

onMounted(loadApps)
</script>
