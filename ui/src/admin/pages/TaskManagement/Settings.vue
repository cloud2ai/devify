<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('taskManagement.settings.moduleConfigTitle') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('taskManagement.settings.moduleConfigSubtitle') }}
        </p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div class="p-6">
          <TaskConfigSection />
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import TaskConfigSection from '@/components/task-management/TaskConfigSection.vue'

const { t } = useI18n()
</script>
