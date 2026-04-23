<template>
  <div class="markdown-preview" v-html="renderedContent"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: {
    type: [String, Object, Array],
    default: ''
  },
  maxLength: {
    type: Number,
    default: 200
  }
})

// Configure marked for preview (simpler, no syntax highlighting)
const previewRenderer = new marked.Renderer()

// Override some renderers for cleaner preview
previewRenderer.heading = (text, level) => {
  return `<strong>${text}</strong>`
}

previewRenderer.list = (tokensOrHtml, ordered) => {
  const toText = (val) => {
    if (!val) return ''
    if (typeof val === 'string') return val
    if (Array.isArray(val)) {
      return val
        .map((t) => {
          if (typeof t === 'string') return t
          if (typeof t === 'object' && t !== null)
            return t?.text || t?.raw || JSON.stringify(t)
          return String(t)
        })
        .filter(Boolean)
        .join(' ')
    }
    if (typeof val === 'object' && val !== null) {
      return val.text || val.raw || JSON.stringify(val)
    }
    return String(val)
  }
  const body = toText(tokensOrHtml)
  return `<div class="list-preview">${body}</div>`
}

previewRenderer.listitem = (tokenOrText) => {
  let text
  if (typeof tokenOrText === 'string') {
    text = tokenOrText
  } else if (tokenOrText && typeof tokenOrText === 'object') {
    text = tokenOrText.text || tokenOrText.raw || JSON.stringify(tokenOrText)
  } else {
    text = String(tokenOrText)
  }
  return `<span class="list-item">• ${text}</span>`
}

const renderedContent = computed(() => {
  if (!props.content) return ''

  try {
    // Normalize to string and truncate for preview
    let raw
    if (typeof props.content === 'string') {
      raw = props.content
    } else if (Array.isArray(props.content)) {
      raw = props.content
        .map((v) => (typeof v === 'string' ? v : JSON.stringify(v)))
        .join(' ')
    } else if (typeof props.content === 'object') {
      // Handle object case - try to extract meaningful content
      raw =
        props.content.content ||
        props.content.text ||
        props.content.summary ||
        JSON.stringify(props.content)
    } else {
      raw = String(props.content)
    }

    const truncatedContent =
      raw.length > props.maxLength
        ? raw.substring(0, props.maxLength) + '...'
        : raw

    const result = marked.parse(truncatedContent, { renderer: previewRenderer })
    return result
  } catch (error) {
    // Fallback to plain text if markdown parsing fails
    const fallback =
      typeof props.content === 'string'
        ? props.content
        : typeof props.content === 'object'
          ? props.content?.content ||
            props.content?.text ||
            JSON.stringify(props.content)
          : String(props.content)
    return (
      fallback.substring(0, props.maxLength) +
      (fallback.length > props.maxLength ? '...' : '')
    )
  }
})
</script>

<style scoped>
.markdown-preview {
  @apply text-sm text-gray-500;
}

.markdown-preview :deep(p) {
  @apply mb-1 last:mb-0;
}

.markdown-preview :deep(strong) {
  @apply font-medium text-gray-700;
}

.markdown-preview :deep(em) {
  @apply italic;
}

.markdown-preview :deep(code) {
  @apply bg-gray-100 text-gray-700 px-1 rounded text-xs;
}

.markdown-preview :deep(.list-preview) {
  @apply space-y-1;
}

.markdown-preview :deep(.list-item) {
  @apply block;
}

.markdown-preview :deep(a) {
  @apply text-primary-600 hover:text-primary-700;
}

.markdown-preview :deep(img) {
  @apply max-w-full h-auto rounded;
}
</style>
