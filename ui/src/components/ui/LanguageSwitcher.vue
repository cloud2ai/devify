<template>
  <div class="relative" ref="dropdownRef">
    <button
      @click="toggleDropdown"
      :class="triggerClass"
      :title="t('common.language')"
    >
      <!-- Language icon -->
      <svg
        class="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
        />
      </svg>
      <!-- Current language flag/name -->
      <span class="text-xs font-medium">{{ currentLanguageDisplay }}</span>
    </button>

    <!-- Dropdown menu -->
    <Transition
      enter-active-class="transition ease-out duration-100"
      enter-from-class="transform opacity-0 scale-95"
      enter-to-class="transform opacity-100 scale-100"
      leave-active-class="transition ease-in duration-75"
      leave-from-class="transform opacity-100 scale-100"
      leave-to-class="transform opacity-0 scale-95"
    >
      <div
        v-if="showDropdown"
        class="absolute right-0 mt-2 w-32 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200"
      >
        <button
          v-for="lang in languages"
          :key="lang.value"
          @click="selectLanguage(lang.value)"
          class="flex items-center w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
          :class="{ 'bg-gray-50 font-medium': locale === lang.value }"
        >
          <span class="mr-2 text-sm">{{ lang.flag }}</span>
          {{ lang.label }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import i18n from '@/i18n'

const props = defineProps({
  variant: {
    type: String,
    default: 'light'
  }
})

const { t, locale } = useI18n()

const showDropdown = ref(false)
const dropdownRef = ref(null)

const languages = [
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'es', label: 'Español', flag: '🇪🇸' }
]

const currentLanguageDisplay = computed(() => {
  const lang = languages.find((l) => l.value === locale.value)
  return lang ? lang.flag : '🌐'
})

const triggerClass = computed(() => {
  return props.variant === 'dark'
    ? 'flex items-center space-x-1 rounded-lg px-2 py-1 text-sm text-slate-300 transition-colors hover:bg-white/10 hover:text-white'
    : 'flex items-center space-x-1 rounded-md px-2 py-1 text-sm text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900'
})

const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value
}

const selectLanguage = (language) => {
  // Only update UI display language, do not sync to AI prompt language
  locale.value = language
  i18n.global.locale.value = language
  localStorage.setItem('userLanguage', language)
  showDropdown.value = false
}

const handleClickOutside = (event) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
