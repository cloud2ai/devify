<template>
  <div class="markdown-content prose max-w-none" v-html="renderedContent"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'

// Import common languages for syntax highlighting
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import xml from 'highlight.js/lib/languages/xml'

// Register languages
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('json', json)
hljs.registerLanguage('xml', xml)

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  enableHighlight: {
    type: Boolean,
    default: true
  }
})

// Configure marked options
marked.setOptions({
  highlight: function (code, lang) {
    if (props.enableHighlight && lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        // Silently fall back to plain text if highlighting fails
      }
    }
    return code
  },
  breaks: true,
  gfm: true
})

const renderedContent = computed(() => {
  if (!props.content) return ''

  try {
    return marked.parse(props.content)
  } catch (error) {
    console.error('Markdown parsing error:', error)
    return `<pre>${props.content}</pre>`
  }
})
</script>

<style scoped>
.markdown-content {
  @apply text-gray-700;
}

/* Override prose styles for better readability */
.markdown-content :deep(h1) {
  @apply text-xl font-bold text-gray-900 mt-6 mb-4 first:mt-0;
}

.markdown-content :deep(h2) {
  @apply text-lg font-semibold text-gray-900 mt-5 mb-3 first:mt-0;
}

.markdown-content :deep(h3) {
  @apply text-base font-medium text-gray-900 mt-4 mb-2 first:mt-0;
}

.markdown-content :deep(h4) {
  @apply text-sm font-medium text-gray-900 mt-3 mb-2 first:mt-0;
}

.markdown-content :deep(p) {
  @apply mb-3 leading-relaxed;
}

.markdown-content :deep(ul) {
  @apply list-disc list-outside mb-3 space-y-1 ml-6;
}

.markdown-content :deep(ol) {
  @apply list-decimal list-outside mb-3 space-y-1 ml-6;
}

.markdown-content :deep(li) {
  @apply text-gray-700;
}

.markdown-content :deep(blockquote) {
  @apply border-l-4 border-gray-300 pl-4 italic text-gray-600 my-4;
}

.markdown-content :deep(code) {
  @apply bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono;
}

.markdown-content :deep(pre) {
  @apply bg-gray-900 border border-gray-700 p-4 rounded-lg my-4 text-sm overflow-x-auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-all;
}

.markdown-content :deep(pre code) {
  @apply bg-transparent p-0 text-gray-100;
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-all;
}

/* Custom styles for code highlighting - terminal theme */
.markdown-content :deep(.hljs) {
  @apply bg-gray-900;
}

.markdown-content :deep(table) {
  @apply w-full border-collapse border border-gray-300 my-4;
}

.markdown-content :deep(th) {
  @apply bg-gray-50 border border-gray-300 px-3 py-2 text-left font-medium text-gray-900;
}

.markdown-content :deep(td) {
  @apply border border-gray-300 px-3 py-2 text-gray-700;
}

.markdown-content :deep(a) {
  @apply text-primary-600 hover:text-primary-700 underline;
}

.markdown-content :deep(img) {
  @apply max-w-full h-auto rounded-lg shadow-md my-4;
}

.markdown-content :deep(strong) {
  @apply font-semibold text-gray-900;
}

.markdown-content :deep(em) {
  @apply italic;
}

.markdown-content :deep(hr) {
  @apply border-t border-gray-300 my-6;
}
</style>
