<template>
  <BaseCard v-if="attachments.length" :header-muted="true">
    <template #header>
      <div class="flex items-center gap-2 text-gray-800">
        <svg
          class="w-5 h-5 -mt-px flex-none"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
          />
        </svg>
        <h3 class="text-base font-semibold leading-5">
          {{ t('chats.files.title') }}
          <span class="text-gray-400 font-normal"
            >({{ attachments.length }})</span
          >
        </h3>
      </div>
    </template>

    <div
      class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3"
    >
      <div
        v-for="att in attachments"
        :key="att.id"
        class="group relative rounded-lg border border-gray-200 bg-white overflow-hidden hover:shadow-sm transition-shadow"
      >
        <!-- Preview / icon area (square) -->
        <button
          type="button"
          class="block w-full aspect-square bg-gray-50 overflow-hidden"
          :title="att.filename"
          @click="onTileClick(att)"
        >
          <img
            v-if="isImage(att) && att.url"
            :src="att.url"
            :alt="att.filename"
            loading="lazy"
            class="w-full h-full object-cover transition-transform group-hover:scale-105"
          />
          <span
            v-else
            class="w-full h-full flex flex-col items-center justify-center gap-2"
          >
            <span
              class="flex h-11 w-11 items-center justify-center rounded-lg"
              :class="chipClass(att)"
            >
              <span class="text-xs font-bold tracking-wide uppercase">
                {{ extLabel(att) }}
              </span>
            </span>
          </span>
        </button>

        <!-- Footer: filename + download -->
        <div
          class="flex items-center gap-1 px-2 py-1.5 border-t border-gray-100"
        >
          <span
            class="flex-1 min-w-0 truncate text-xs text-gray-700"
            :title="att.filename"
          >
            {{ att.filename }}
          </span>
          <a
            v-if="att.url"
            :href="att.url"
            :download="att.filename"
            class="flex-none text-gray-400 hover:text-blue-600"
            :title="t('chats.files.download')"
            @click.stop
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </a>
        </div>

        <!-- Size badge -->
        <span
          v-if="att.file_size != null"
          class="absolute top-1 left-1 rounded bg-black/50 px-1 py-0.5 text-[10px] leading-none text-white"
        >
          {{ formatBytes(att.file_size) }}
        </span>
      </div>
    </div>

    <!-- Preview modal (image or text) -->
    <Teleport to="body">
      <div
        v-if="preview"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
        @click="closePreview"
      >
        <img
          v-if="preview.type === 'image'"
          :src="preview.att.url"
          :alt="preview.att.filename"
          class="max-h-[90vh] max-w-[90vw] object-contain rounded shadow-xl"
          @click.stop
        />

        <div
          v-else
          class="flex w-full flex-col overflow-hidden rounded-lg bg-white shadow-xl"
          :class="
            preview.type === 'pdf'
              ? 'max-w-5xl h-[90vh]'
              : 'max-w-3xl max-h-[85vh]'
          "
          @click.stop
        >
          <div
            class="flex items-center gap-2 border-b border-gray-200 px-4 py-2.5"
          >
            <span
              class="flex-1 min-w-0 truncate text-sm font-medium text-gray-800"
            >
              {{ preview.att.filename }}
            </span>
            <a
              :href="preview.att.url"
              :download="preview.att.filename"
              class="flex-none text-xs font-medium text-blue-600 hover:text-blue-800"
            >
              {{ t('chats.files.download') }}
            </a>
            <button
              type="button"
              class="flex-none text-gray-400 hover:text-gray-700"
              :aria-label="t('common.close')"
              @click="closePreview"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <iframe
            v-if="preview.type === 'pdf'"
            :src="preview.att.url"
            :title="preview.att.filename"
            class="flex-1 w-full border-0"
          />
          <div v-else class="flex-1 overflow-auto p-4">
            <div v-if="preview.loading" class="text-sm text-gray-500 italic">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="preview.error" class="text-sm text-red-500">
              {{ preview.error }}
            </div>
            <pre
              v-else
              class="whitespace-pre-wrap break-words text-xs text-gray-700"
              >{{ preview.content }}</pre
            >
          </div>
        </div>

        <button
          v-if="preview.type === 'image'"
          type="button"
          class="absolute top-4 right-4 text-white/80 hover:text-white"
          :aria-label="t('common.close')"
          @click="closePreview"
        >
          <svg
            class="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </Teleport>
  </BaseCard>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseCard from '@/components/ui/BaseCard.vue'
import { formatBytes } from '@/utils/formatting'

const { t } = useI18n()

defineProps({
  attachments: {
    type: Array,
    default: () => []
  }
})

const TEXT_CONTENT_TYPES = [
  'application/json',
  'application/xml',
  'application/x-yaml',
  'application/yaml',
  'application/x-sh'
]

// Extension -> colored chip. Lets Word/Excel/PDF/etc. read as intentional
// file types instead of a generic gray icon.
const TYPE_COLORS = {
  pdf: 'bg-red-50 text-red-600',
  doc: 'bg-blue-50 text-blue-600',
  docx: 'bg-blue-50 text-blue-600',
  xls: 'bg-green-50 text-green-600',
  xlsx: 'bg-green-50 text-green-600',
  csv: 'bg-green-50 text-green-600',
  ppt: 'bg-orange-50 text-orange-600',
  pptx: 'bg-orange-50 text-orange-600',
  zip: 'bg-amber-50 text-amber-600',
  rar: 'bg-amber-50 text-amber-600',
  '7z': 'bg-amber-50 text-amber-600'
}

const MAX_TEXT_PREVIEW = 100000

function isImage(att) {
  return (
    att.is_image || (att.content_type || '').toLowerCase().startsWith('image/')
  )
}

function isText(att) {
  const ct = (att.content_type || '').toLowerCase()
  return ct.startsWith('text/') || TEXT_CONTENT_TYPES.includes(ct)
}

function isPdf(att) {
  return (
    (att.content_type || '').toLowerCase() === 'application/pdf' ||
    ext(att) === 'pdf'
  )
}

// Full file extension (lowercased), used for type logic (isPdf, chipClass).
function ext(att) {
  const name = att.filename || ''
  const dot = name.lastIndexOf('.')
  if (dot >= 0 && dot < name.length - 1) {
    return name.slice(dot + 1).toLowerCase()
  }
  return ''
}

// Short label for the type chip; falls back to a generic "file" word.
function extLabel(att) {
  const e = ext(att)
  return e ? e.slice(0, 4) : t('chats.files.file')
}

function chipClass(att) {
  return TYPE_COLORS[ext(att)] || 'bg-gray-100 text-gray-500'
}

// Unified preview modal state (image or text), null when closed
const preview = ref(null)

function onTileClick(att) {
  if (!att.url) return
  if (isImage(att)) {
    preview.value = { type: 'image', att }
  } else if (isPdf(att)) {
    preview.value = { type: 'pdf', att }
  } else if (isText(att)) {
    openTextPreview(att)
  } else {
    // Non-previewable (Word/Excel/PPT/archives): download instead
    triggerDownload(att)
  }
}

async function openTextPreview(att) {
  preview.value = {
    type: 'text',
    att,
    loading: true,
    error: '',
    content: ''
  }
  const state = preview.value
  try {
    // Request only the head of the file via a Range request so a huge
    // attachment is not fully buffered into memory just to show a preview.
    // nginx serves byte ranges on static files; if it ignores the header we
    // still cap the text below. Note: att.url is same-origin (relative) here;
    // a cross-origin ATTACHMENT_BASE_URL would need CORS for this fetch.
    const res = await fetch(att.url, {
      headers: { Range: `bytes=0-${MAX_TEXT_PREVIEW - 1}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    let text = await res.text()
    if (text.length > MAX_TEXT_PREVIEW) {
      text = text.slice(0, MAX_TEXT_PREVIEW) + '\n…'
    }
    // Ignore if the modal was closed/switched while fetching
    if (preview.value !== state) return
    state.content = text
  } catch (e) {
    if (preview.value !== state) return
    state.error = t('chats.files.previewError')
  } finally {
    if (preview.value === state) state.loading = false
  }
}

// Relies on the anchor `download` attribute, which browsers honor only for
// same-origin URLs. att.url is relative/same-origin in this deployment; a
// cross-origin ATTACHMENT_BASE_URL would open the file in-tab instead of
// saving it and would need a blob-based download.
function triggerDownload(att) {
  const a = document.createElement('a')
  a.href = att.url
  a.download = att.filename || ''
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function closePreview() {
  preview.value = null
}
</script>
