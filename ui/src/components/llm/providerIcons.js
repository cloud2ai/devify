const LOCAL_PROVIDER_ICON_MODULES = import.meta.glob(
  '/src/assets/provider-icons/lobehub/*.svg',
  { eager: true, import: 'default' }
)

const LOCAL_PROVIDER_ICON_URLS = Object.fromEntries(
  Object.entries(LOCAL_PROVIDER_ICON_MODULES).map(([filePath, iconUrl]) => {
    const fileName = filePath.split('/').pop() || ''
    const providerSlug = fileName.replace(/\.svg$/, '')
    return [providerSlug, iconUrl]
  })
)

const PROVIDER_ICON_ALIASES = {
  amazon_nova: 'aws',
  azure_openai: 'azure',
  claude: 'anthropic',
  dashscope: 'qwen',
  meta_llama: 'meta',
  nvidia_nim: 'nvidia',
  zai: 'zhipu'
}

/** Brand color for fallback letter circle. */
export const PROVIDER_COLORS = {
  openai: '#412991',
  azure_openai: '#0078D4',
  gemini: '#4285F4',
  anthropic: '#D4A574',
  mistral: '#6366F1',
  dashscope: '#FF6A00',
  deepseek: '#1E40AF',
  xai: '#1a1a1a',
  minimax: '#1E3A5F',
  moonshot: '#6366F1',
  zai: '#2D5AFF',
  volcengine: '#E23B2F',
  openrouter: '#B83280',
  meta_llama: '#0668E1',
  amazon_nova: '#FF9900',
  nvidia_nim: '#76B900'
}

const DEFAULT_COLOR = '#64748b'

function normalizeProviderKey(provider) {
  return String(provider || '')
    .trim()
    .toLowerCase()
}

function resolveProviderSlug(provider) {
  const key = normalizeProviderKey(provider)
  if (!key) return null

  const alias = PROVIDER_ICON_ALIASES[key]
  if (alias && LOCAL_PROVIDER_ICON_URLS[alias]) return alias

  if (LOCAL_PROVIDER_ICON_URLS[key]) return key

  const compactKey = key.replace(/[_\s-]/g, '')
  if (LOCAL_PROVIDER_ICON_URLS[compactKey]) return compactKey

  if (key.startsWith('azure') && LOCAL_PROVIDER_ICON_URLS.azure) return 'azure'
  if (key.startsWith('meta') && LOCAL_PROVIDER_ICON_URLS.meta) return 'meta'
  if (key.startsWith('amazon') && LOCAL_PROVIDER_ICON_URLS.aws) return 'aws'
  if (key.startsWith('nvidia') && LOCAL_PROVIDER_ICON_URLS.nvidia) {
    return 'nvidia'
  }

  return null
}

export function getProviderIconUrl(provider) {
  const slug = resolveProviderSlug(provider)
  if (!slug) return null
  return LOCAL_PROVIDER_ICON_URLS[slug] || null
}

export function getProviderColor(provider) {
  const key = normalizeProviderKey(provider).replace(/\s+/g, '_')
  return PROVIDER_COLORS[key] || DEFAULT_COLOR
}

export function getProviderFallbackLetter(provider) {
  if (!provider || typeof provider !== 'string') return '?'
  if (provider.startsWith('azure')) return 'A'
  if (provider.startsWith('meta')) return 'M'
  if (provider.startsWith('amazon')) return 'A'
  if (provider.startsWith('nvidia')) return 'N'
  if (provider.startsWith('xai')) return 'x'
  return (provider[0] || '?').toUpperCase()
}
