<template>
  <BaseModal :show="show" :title="t('retry.dialogTitle')" @close="handleClose">
    <div v-if="initializing" class="flex items-center justify-center py-8">
      <div class="text-center">
        <svg
          class="animate-spin h-8 w-8 text-primary-600 mx-auto"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <p class="mt-4 text-sm text-gray-600">{{ t('common.loading') }}</p>
      </div>
    </div>
    <div v-else class="space-y-4">
      <!-- Language Selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('settings.language') }}
        </label>
        <select
          v-model="localLanguage"
          class="input w-full"
          :disabled="loading"
        >
          <option value="">{{ t('retry.useDefaultLanguage') }}</option>
          <option value="en-US">{{ t('settings.languages.en') }}</option>
          <option value="zh-CN">{{ t('settings.languages.zh-CN') }}</option>
          <option value="es">{{ t('settings.languages.es') }}</option>
        </select>
      </div>

      <!-- Scene Selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('settings.scene') }}
        </label>
        <select
          v-model="localScene"
          class="input w-full"
          :disabled="loading || loadingScenes"
        >
          <option value="" disabled>
            {{ loadingScenes ? t('common.loading') : t('auth.selectScene') }}
          </option>
          <option v-for="scene in scenes" :key="scene.key" :value="scene.key">
            {{ scene.name
            }}{{ scene.description ? ` - ${scene.description}` : '' }}
          </option>
        </select>
      </div>

      <!-- Force Option -->
      <div class="border-t border-gray-200 pt-4">
        <div class="flex items-center gap-3">
          <div class="flex items-center flex-shrink-0">
            <input
              id="force-retry"
              v-model="localForce"
              type="checkbox"
              class="focus:ring-primary-500 h-4 w-4 text-primary-600 border-gray-300 rounded"
              :disabled="loading || forceRequired"
            />
          </div>
          <div class="flex-1 min-w-0">
            <label
              for="force-retry"
              class="block text-sm font-medium text-gray-700 cursor-pointer"
            >
              {{ t('retry.forceMode') }}
            </label>
          </div>
        </div>
        <div class="mt-2">
          <div
            class="py-3 px-4 sm:px-6 bg-yellow-50 border border-yellow-200 rounded-md"
          >
            <div class="flex gap-2">
              <div class="flex-shrink-0">
                <svg
                  class="h-5 w-5 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-yellow-800 leading-relaxed">
                  {{ t('retry.forceModeWarning') }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div
        class="w-full flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2"
      >
        <BaseButton
          variant="secondary"
          @click="handleClose"
          :disabled="loading"
          class="w-full sm:w-auto"
        >
          {{ t('common.cancel') }}
        </BaseButton>
        <BaseButton
          variant="primary"
          @click="handleRetry"
          :loading="loading"
          class="w-full sm:w-auto"
        >
          {{ t('retry.confirmRetry') }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { authApi } from '@/api/auth'
import { settingsApi } from '@/api/settings'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  status: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'confirm'])

const { t, locale } = useI18n()

const loading = ref(false)
const loadingScenes = ref(false)
const initializing = ref(false)
const localLanguage = ref('')
const localScene = ref('')
const localForce = ref(false)
const scenes = ref([])
const defaultLanguage = ref('')
const defaultScene = ref('')

// Check if force retry is required (for success status)
const forceRequired = computed(() => {
  return props.status === 'success'
})

// Note: Backend returns language in en-US format, and we use en-US format in options
// This matches the backend API expectations

const loadDefaults = async () => {
  try {
    const preferences = await settingsApi.getPreferences()
    defaultLanguage.value = preferences.language || ''
    defaultScene.value = preferences.scene || ''
  } catch (error) {
    console.error('Failed to load user preferences:', error)
  }
}

const loadScenes = async () => {
  loadingScenes.value = true
  try {
    const response = await authApi.getAvailableScenes(locale.value)
    const responseData = response.data.data || response.data || []
    scenes.value = Array.isArray(responseData) ? responseData : []
  } catch (error) {
    console.error('Failed to load scenes:', error)
  } finally {
    loadingScenes.value = false
  }
}

const handleClose = () => {
  emit('close')
}

const handleRetry = () => {
  emit('confirm', {
    language: localLanguage.value || null,
    scene: localScene.value || null,
    force: localForce.value
  })
}

watch(
  () => props.show,
  async (newValue) => {
    if (newValue) {
      initializing.value = true
      // Set force based on status: if success, force must be true
      localForce.value = forceRequired.value
      // Reset to empty first
      localLanguage.value = ''
      localScene.value = ''

      // Load defaults and scenes in parallel
      await Promise.all([loadDefaults(), loadScenes()])

      // Set defaults after loading both preferences and scenes
      // This ensures the select options are populated before setting values
      if (defaultLanguage.value) {
        localLanguage.value = defaultLanguage.value
      }
      if (
        defaultScene.value &&
        scenes.value.some((s) => s.key === defaultScene.value)
      ) {
        localScene.value = defaultScene.value
      } else if (scenes.value.length > 0 && !localScene.value) {
        // If default scene not found, use first available scene
        localScene.value = scenes.value[0].key
      }

      initializing.value = false
    }
  }
)

onMounted(async () => {
  if (props.show) {
    initializing.value = true
    // Set force based on status: if success, force must be true
    localForce.value = forceRequired.value
    await Promise.all([loadDefaults(), loadScenes()])
    // Set defaults after loading both preferences and scenes
    if (defaultLanguage.value) {
      localLanguage.value = defaultLanguage.value
    }
    if (
      defaultScene.value &&
      scenes.value.some((s) => s.key === defaultScene.value)
    ) {
      localScene.value = defaultScene.value
    } else if (scenes.value.length > 0 && !localScene.value) {
      localScene.value = scenes.value[0].key
    }
    initializing.value = false
  }
})
</script>

<style scoped>
.input {
  @apply block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500;
  @apply text-sm;
  @apply px-3 py-2;
  @apply min-h-[44px] sm:min-h-[36px]; /* Better touch target on mobile */
}
</style>
