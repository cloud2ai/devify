<template>
  <AdminLayout>
    <div class="w-full max-w-full p-6 pb-28">
      <div class="mb-4">
        <h1 class="text-lg font-semibold text-gray-900">
          {{ t('threadline.periodicTasks.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500">
          {{ t('threadline.periodicTasks.subtitle') }}
        </p>
      </div>

      <div
        class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
      >
        <div class="p-6">
          <BaseLoading v-if="loading" />

          <template v-else>
            <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
              <div>
                <h2 class="text-base font-semibold text-gray-900">
                  {{ t('threadline.periodicTasks.sectionTitle') }}
                </h2>
                <p class="text-sm text-gray-500 mt-1">
                  {{ t('threadline.periodicTasks.crontabHint') }}
                </p>
              </div>
              <div class="text-sm text-gray-500">
                {{
                  t('threadline.periodicTasks.summary', {
                    total: tasks.length,
                    enabled: enabledCount
                  })
                }}
              </div>
            </div>

            <div
              class="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
            >
              {{ t('threadline.periodicTasks.autoSaveHint') }}
            </div>

            <div class="space-y-4">
              <div
                v-for="task in tasks"
                :key="task.name"
                class="rounded-lg border border-gray-200 bg-gray-50 p-4"
              >
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
                  <div class="lg:col-span-2 min-w-0">
                    <div class="flex flex-wrap items-center gap-2 mb-2">
                      <h4 class="text-sm font-semibold text-gray-900">
                        {{ getTaskTitle(task) }}
                      </h4>
                      <span
                        class="text-[11px] px-2 py-0.5 rounded-full bg-gray-200 text-gray-600 font-medium"
                      >
                        threadline
                      </span>
                    </div>
                    <p class="text-sm text-gray-600">
                      {{ getTaskDescription(task) }}
                    </p>
                    <p class="text-xs text-gray-500 mt-2 font-mono break-all">
                      {{ task.task }}
                    </p>
                  </div>

                  <div class="lg:col-span-1 flex flex-col gap-3 lg:items-end">
                    <div
                      class="w-full flex items-center justify-between lg:justify-end gap-3"
                    >
                      <span class="text-sm font-medium text-gray-700">
                        {{ t('threadline.periodicTasks.enabled') }}
                      </span>
                      <label
                        class="relative inline-flex items-center cursor-pointer"
                      >
                        <input
                          :checked="task.enabled"
                          type="checkbox"
                          :disabled="busy || isTaskSaving(task.name)"
                          @change="handleTaskEnabledChange(task, $event)"
                          class="sr-only peer"
                        />
                        <div
                          class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"
                        />
                      </label>
                    </div>

                    <div class="w-full">
                      <label class="text-sm font-medium text-gray-700">
                        {{ t('threadline.periodicTasks.crontab') }}
                      </label>
                      <input
                        v-model="task.crontab"
                        type="text"
                        :disabled="
                          !task.enabled || busy || isTaskSaving(task.name)
                        "
                        :placeholder="
                          t('threadline.periodicTasks.crontabPlaceholder')
                        "
                        class="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm w-full font-mono focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
                      />
                      <p class="text-xs text-gray-500 mt-0.5">
                        {{ t('threadline.periodicTasks.crontabHelp') }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
    <div
      class="fixed inset-x-0 bottom-0 z-30 border-t border-gray-200 bg-white/95 backdrop-blur lg:left-64"
    >
      <div
        class="mx-auto flex w-full max-w-full items-center justify-between gap-4 px-6 py-4"
      >
        <div class="text-sm text-gray-500">
          {{ t('threadline.periodicTasks.footerHint') }}
        </div>
        <div class="flex items-center gap-3">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="busy"
            @click="resetForm"
          >
            {{ t('threadline.periodicTasks.reset') }}
          </BaseButton>
          <BaseButton
            variant="primary"
            size="sm"
            :loading="saving"
            :disabled="busy"
            @click="saveConfig"
          >
            {{ t('threadline.periodicTasks.saveChanges') }}
          </BaseButton>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage, extractResponseData } from '@/utils/api'
import AdminLayout from '@/admin/layout/AdminLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { periodicTasksApi } from '@/admin/api/periodicTasks'

const { t } = useI18n()
const { showSuccess, showError } = useToast()

const loading = ref(false)
const saving = ref(false)
const savingTaskNames = ref(new Set())
const tasks = ref([])
const initialTasks = ref([])

const taskMeta = {
  schedule_email_fetch: {
    titleKey: 'threadline.periodicTasks.tasks.emailFetch.title',
    descKey: 'threadline.periodicTasks.tasks.emailFetch.description'
  },
  reset_stuck_emails: {
    titleKey: 'threadline.periodicTasks.tasks.resetStuckEmails.title',
    descKey: 'threadline.periodicTasks.tasks.resetStuckEmails.description'
  },
  schedule_haraka_cleanup: {
    titleKey: 'threadline.periodicTasks.tasks.harakaCleanup.title',
    descKey: 'threadline.periodicTasks.tasks.harakaCleanup.description'
  },
  schedule_email_task_cleanup: {
    titleKey: 'threadline.periodicTasks.tasks.emailTaskCleanup.title',
    descKey: 'threadline.periodicTasks.tasks.emailTaskCleanup.description'
  },
  schedule_share_link_cleanup: {
    titleKey: 'threadline.periodicTasks.tasks.shareLinkCleanup.title',
    descKey: 'threadline.periodicTasks.tasks.shareLinkCleanup.description'
  }
}

function cloneTasks(source) {
  return JSON.parse(JSON.stringify(source || []))
}

function normalizeTask(task) {
  const crontab =
    String(task?.crontab || '').trim() || task?.default_crontab || '0 2 * * *'
  return {
    name: task?.name,
    task: task?.task,
    module: task?.module || 'other',
    label: task?.label || task?.name,
    description: task?.description || '',
    enabled: task?.enabled !== false,
    crontab,
    default_enabled: task?.default_enabled !== false,
    default_crontab: task?.default_crontab || crontab
  }
}

const enabledCount = computed(
  () => tasks.value.filter((task) => task.enabled).length
)

const busy = computed(() => saving.value || savingTaskNames.value.size > 0)

function isTaskSaving(name) {
  return savingTaskNames.value.has(name)
}

function setTaskSaving(name, isSaving) {
  const next = new Set(savingTaskNames.value)
  if (isSaving) {
    next.add(name)
  } else {
    next.delete(name)
  }
  savingTaskNames.value = next
}

function snapshotTasks() {
  initialTasks.value = cloneTasks(tasks.value)
}

function getTaskTitle(task) {
  const meta = taskMeta[task?.name] || {}
  return meta.titleKey ? t(meta.titleKey) : task?.label || task?.name || '-'
}

function getTaskDescription(task) {
  const meta = taskMeta[task?.name] || {}
  return meta.descKey ? t(meta.descKey) : task?.description || ''
}

function resetForm() {
  tasks.value = cloneTasks(initialTasks.value)
}

async function saveSingleTask(task) {
  const crontab = String(task?.crontab || '').trim()
  if (!crontab) {
    showError(t('threadline.periodicTasks.crontabRequired'))
    task.enabled = !task.enabled
    return
  }

  setTaskSaving(task.name, true)
  try {
    const response = await periodicTasksApi.updateSettings({
      tasks: [
        {
          name: task.name,
          enabled: !!task.enabled,
          crontab
        }
      ]
    })
    const data = extractResponseData(response)
    const list = Array.isArray(data?.tasks) ? data.tasks : []
    tasks.value = list.map(normalizeTask)
    snapshotTasks()
  } catch (error) {
    task.enabled = !task.enabled
    showError(
      extractErrorMessage(error, t('threadline.periodicTasks.saveFailed'))
    )
  } finally {
    setTaskSaving(task.name, false)
  }
}

function handleTaskEnabledChange(task, event) {
  task.enabled = event.target.checked
  saveSingleTask(task)
}

async function loadConfig() {
  loading.value = true
  try {
    const response = await periodicTasksApi.getSettings()
    const data = extractResponseData(response)
    const list = Array.isArray(data?.tasks) ? data.tasks : []
    tasks.value = list.map(normalizeTask)
    snapshotTasks()
  } catch (error) {
    tasks.value = []
    initialTasks.value = []
    showError(
      extractErrorMessage(error, t('threadline.periodicTasks.loadFailed'))
    )
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  const payloadTasks = tasks.value.map((task) => ({
    name: task.name,
    enabled: !!task.enabled,
    crontab: String(task.crontab || '').trim()
  }))

  if (payloadTasks.some((task) => !task.crontab)) {
    showError(t('threadline.periodicTasks.crontabRequired'))
    return
  }

  saving.value = true
  try {
    const response = await periodicTasksApi.updateSettings({
      tasks: payloadTasks
    })
    const data = extractResponseData(response)
    const list = Array.isArray(data?.tasks) ? data.tasks : []
    tasks.value = list.map(normalizeTask)
    snapshotTasks()
    showSuccess(t('threadline.periodicTasks.saveSuccess'))
  } catch (error) {
    showError(
      extractErrorMessage(error, t('threadline.periodicTasks.saveFailed'))
    )
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>
