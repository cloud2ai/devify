<template>
  <div class="w-full">
    <template v-if="isMobile">
      <input
        :class="mobileInputClasses"
        type="datetime-local"
        :value="nativeValue"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="onNativeInput"
      />
    </template>
    <template v-else>
      <VueDatePicker
        :model-value="internalValue"
        @update:model-value="onPickerUpdate"
        :enable-time-picker="true"
        :teleport="true"
        :teleport-center="true"
        :auto-apply="autoApply"
        :clearable="clearable"
        :disabled="disabled"
        :placeholder="placeholder"
        :format="resolvedFormat"
        :is-24="true"
        :locale="pickerLocale"
        :class="desktopWrapperClass"
        :input-class="inputClasses"
        :hide-input-icon="hideInputIcon"
        :action-row="actionRowConfig"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue'
import { format } from 'date-fns'
import { enUS, zhCN, es } from 'date-fns/locale'
import { useI18n } from 'vue-i18n'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import { usePreferencesStore } from '@/store/preferences'

const props = defineProps({
  modelValue: {
    type: [String, Date, null],
    default: null
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  clearable: {
    type: Boolean,
    default: true
  },
  pickerFormat: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'compact'].includes(value)
  },
  showActions: {
    type: Boolean,
    default: true
  },
  showInputIcon: {
    type: Boolean,
    default: true
  },
  confirmLabel: {
    type: String,
    default: ''
  },
  cancelLabel: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])
const { t, locale } = useI18n()
const preferencesStore = usePreferencesStore()

const internalValue = ref(null)
const isMobile = ref(false)
let mediaQuery
const wrapperClassMap = {
  default: 'w-full text-sm',
  compact: 'w-full text-xs'
}

const commonInput =
  'w-full border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 disabled:cursor-not-allowed'
const sizeMap = {
  default: {
    input: `${commonInput} px-2.5 py-1.5 text-sm h-10`,
    mobile: `${commonInput} px-3 py-2 text-sm`
  },
  compact: {
    input: `${commonInput} px-2 py-0.5 text-xs h-5`,
    mobile: `${commonInput} px-2 py-0.5 text-xs`
  }
}

const inputClasses = computed(() => sizeMap[props.size].input)
const mobileInputClasses = computed(() => sizeMap[props.size].mobile)
const desktopWrapperClass = computed(() => {
  const classes = [wrapperClassMap[props.size]]
  if (props.size === 'compact') {
    classes.push('bdtp-compact')
  }
  return classes
})
const autoApply = computed(() => !props.showActions)
const hideInputIcon = computed(
  () => props.size === 'compact' || !props.showInputIcon
)
const normalizedLanguage = computed(() => {
  const lang = locale.value || preferencesStore.currentLanguage || 'en'
  if (lang.startsWith('zh')) return 'zh-CN'
  if (lang.startsWith('es')) return 'es'
  return 'en'
})
const localeMap = {
  'zh-CN': zhCN,
  zh: zhCN,
  es,
  en: enUS
}
const pickerLocale = computed(() => localeMap[normalizedLanguage.value] || enUS)
const formatMap = {
  'zh-CN': 'yyyy/MM/dd HH:mm',
  es: 'dd/MM/yyyy HH:mm',
  en: 'MM/dd/yyyy, HH:mm'
}
const resolvedFormat = computed(() => {
  if (props.pickerFormat) {
    return props.pickerFormat
  }
  return formatMap[normalizedLanguage.value] || 'yyyy-MM-dd HH:mm'
})
const confirmText = computed(() => props.confirmLabel || t('common.confirm'))
const cancelText = computed(() => props.cancelLabel || t('common.cancel'))
const actionRowConfig = computed(() => ({
  show: props.showActions,
  showSelect: true,
  showCancel: true,
  showNow: false,
  showPreview: false,
  selectBtnLabel: confirmText.value,
  cancelBtnLabel: cancelText.value
}))

const detectMobile = () => {
  if (typeof window === 'undefined') return false
  const touchMatch = window.matchMedia('(pointer: coarse)')
  return touchMatch.matches || window.innerWidth < 640
}

const updateInternalFromProp = (value) => {
  if (!value) {
    internalValue.value = null
    return
  }
  const dateObj = value instanceof Date ? value : new Date(value)
  internalValue.value = Number.isNaN(dateObj.getTime()) ? null : dateObj
}

watch(
  () => props.modelValue,
  (val) => {
    updateInternalFromProp(val)
  },
  { immediate: true }
)

const emitValue = (val) => {
  if (!val) {
    emit('update:modelValue', null)
    return
  }
  const dateObj = val instanceof Date ? val : new Date(val)
  emit(
    'update:modelValue',
    Number.isNaN(dateObj.getTime()) ? null : dateObj.toISOString()
  )
}

const onPickerUpdate = (val) => {
  if (val instanceof Date) {
    internalValue.value = val
    emitValue(val)
  } else if (!val) {
    internalValue.value = null
    emitValue(null)
  }
}

const nativeValue = computed(() => {
  if (!internalValue.value) return ''
  return format(internalValue.value, "yyyy-MM-dd'T'HH:mm")
})

const onNativeInput = (event) => {
  const { value } = event.target
  if (!value) {
    internalValue.value = null
    emitValue(null)
    return
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    internalValue.value = null
    emitValue(null)
  } else {
    internalValue.value = parsed
    emitValue(parsed)
  }
}

onMounted(() => {
  isMobile.value = detectMobile()
  if (typeof window !== 'undefined') {
    mediaQuery = window.matchMedia('(max-width: 640px)')
    const handler = (e) => {
      isMobile.value = e.matches || 'ontouchstart' in window
    }
    mediaQuery.addEventListener?.('change', handler)
    onBeforeUnmount(() => {
      mediaQuery?.removeEventListener?.('change', handler)
    })
  }
})
</script>
