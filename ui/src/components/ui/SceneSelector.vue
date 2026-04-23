<template>
  <div class="scene-selector">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
    </label>

    <select
      v-model="selectedScene"
      @change="handleChange"
      class="input"
      :class="{ 'input-error': error }"
      :disabled="disabled || loading"
    >
      <option value="" disabled>
        {{ loading ? t('common.loading') : t('auth.selectScene') }}
      </option>
      <option v-for="scene in scenes" :key="scene.key" :value="scene.key">
        {{ scene.name }}
      </option>
    </select>

    <p
      v-if="selectedScene && currentSceneDescription"
      class="mt-2 text-sm text-gray-600"
    >
      {{ currentSceneDescription }}
    </p>

    <p v-if="error" class="mt-1 text-sm text-red-600">
      {{ error }}
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getAvailableScenes } from '@/api/auth'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  error: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const { t, locale } = useI18n()

const scenes = ref([])
const loading = ref(false)
const selectedScene = ref(props.modelValue)

const currentSceneDescription = computed(() => {
  const scene = scenes.value.find((s) => s.key === selectedScene.value)
  return scene ? scene.description : ''
})

const loadScenes = async () => {
  loading.value = true
  try {
    const response = await getAvailableScenes(locale.value)

    const responseData = response.data.data || response.data || []
    scenes.value = Array.isArray(responseData) ? responseData : []

    if (scenes.value.length > 0 && !selectedScene.value) {
      selectedScene.value = scenes.value[0].key
      emit('update:modelValue', selectedScene.value)
    }
  } catch (error) {
    console.error('Failed to load scenes:', error)
  } finally {
    loading.value = false
  }
}

const handleChange = () => {
  emit('update:modelValue', selectedScene.value)
}

watch(
  () => props.modelValue,
  (newValue) => {
    selectedScene.value = newValue
  }
)

watch(
  () => locale.value,
  () => {
    loadScenes()
  }
)

onMounted(() => {
  loadScenes()
})
</script>

<style scoped>
.scene-selector {
  width: 100%;
}
</style>
