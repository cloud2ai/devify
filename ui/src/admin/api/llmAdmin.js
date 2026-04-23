/**
 * LLM admin API (agentcore-metering: token-stats, llm-usage, llm-config).
 * Global config: list (GET), add (POST), get/put/delete by id (GET/PUT/DELETE llm-config/<pk>/).
 * Providers schema: GET llm-config/providers/. Test: POST llm-config/test/.
 */
import apiClient from '@/api/index'

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

function extractData(res) {
  const body = res?.data
  if (body && typeof body === 'object' && 'data' in body) return body.data
  return body ?? res
}

export const llmAdminApi = {
  getTokenStats(params = {}) {
    return apiClient.get('/v1/admin/token-stats/', { params }).then(extractData)
  },

  /** GET metering config (retention_days, cleanup, aggregation crontabs). */
  getMeteringConfig() {
    return apiClient.get('/v1/admin/metering-config/').then(extractData)
  },
  /** PATCH metering config. */
  updateMeteringConfig(data) {
    return apiClient.patch('/v1/admin/metering-config/', data).then(extractData)
  },

  getLLMUsage(params = {}) {
    return apiClient.get('/v1/admin/llm-usage/', { params }).then(extractData)
  },

  /** GET global LLM config list (array). */
  getLLMConfig() {
    return apiClient.get('/v1/admin/llm-config/').then(extractData)
  },
  /** GET all LLM configs (global + user). Params: scope=all|global|user, user_id (optional). */
  getLLMConfigAll(params = {}) {
    return apiClient
      .get('/v1/admin/llm-config/all/', { params })
      .then(extractData)
  },
  /** POST add config. Body: { provider, config?, is_active?, order?, scope?, user_id? }. */
  postLLMConfig(body) {
    return apiClient.post('/v1/admin/llm-config/', body).then(extractData)
  },
  getLLMConfigDetail(configUuid) {
    return apiClient
      .get(`/v1/admin/llm-config/${encodeURIComponent(configUuid)}/`)
      .then(extractData)
  },
  putLLMConfigDetail(configUuid, body) {
    return apiClient
      .put(`/v1/admin/llm-config/${encodeURIComponent(configUuid)}/`, body)
      .then(extractData)
  },
  deleteLLMConfigDetail(configUuid) {
    return apiClient.delete(
      `/v1/admin/llm-config/${encodeURIComponent(configUuid)}/`
    )
  },

  /** GET provider schema for dynamic forms. Returns { providers: { [name]: { required, optional, editable_params, default_model, default_api_base } } }. */
  getLLMConfigProviders() {
    return apiClient.get('/v1/admin/llm-config/providers/').then(extractData)
  },
  /** GET provider list and per-provider models with capability tags. Returns { providers: [ { id, label, models: [ { id, label, capabilities, max_input_tokens, max_output_tokens } ] } ], capability_labels }. */
  getLLMConfigModels() {
    return apiClient.get('/v1/admin/llm-config/models/').then(extractData)
  },
  /** POST test config without saving. Body: { provider, config }. Returns { ok: boolean, detail?: string }. */
  postLLMConfigTest(body) {
    return apiClient.post('/v1/admin/llm-config/test/', body).then(extractData)
  },
  /**
   * POST run test call with a saved config. Body: { config_uuid, prompt, max_tokens? }.
   * Sync call; records to LLM usage. Returns { ok, content?, detail?, usage? }.
   * Uses 90s timeout because LLM completion (e.g. reasoning models) can be slow.
   */
  postLLMConfigTestCall(body) {
    return apiClient
      .post('/v1/admin/llm-config/test-call/', body, { timeout: 90000 })
      .then(extractData)
  },

  /**
   * POST test call with stream: true. Response is SSE (text/event-stream).
   * callbacks: { onChunk(content), onReasoning(content), onDone(usage), onError(detail) }.
   * signal: optional AbortSignal to stop the stream (e.g. from AbortController).
   */
  async postLLMConfigTestCallStream(body, callbacks = {}, signal = null) {
    const baseURL = apiClient.defaults.baseURL || ''
    const url = `${baseURL.replace(/\/$/, '')}/v1/admin/llm-config/test-call/`
    const token =
      typeof localStorage !== 'undefined'
        ? localStorage.getItem('access_token')
        : null
    const csrf = getCookie('csrftoken')
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`
    if (csrf) headers['X-CSRFToken'] = csrf
    const fetchOpts = {
      method: 'POST',
      body: JSON.stringify({ ...body, stream: true }),
      headers,
      credentials: 'include'
    }
    if (signal) fetchOpts.signal = signal
    const res = await fetch(url, fetchOpts)
    if (!res.ok) {
      const err = new Error(res.statusText)
      err.response = { status: res.status }
      try {
        const data = await res.json()
        if (data?.detail) err.detail = data.detail
      } catch (readError) {
        void readError
      }
      if (callbacks.onError) callbacks.onError(err.detail || err.message)
      throw err
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    try {
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        for (const part of parts) {
          const line = part.split('\n').find((l) => l.startsWith('data:'))
          if (!line) continue
          try {
            const payload = JSON.parse(line.slice(5).trim())
            if (
              payload.type === 'reasoning' &&
              payload.content != null &&
              callbacks.onReasoning
            ) {
              callbacks.onReasoning(payload.content)
            } else if (
              (payload.type === 'chunk' || payload.type === 'content') &&
              payload.content != null &&
              callbacks.onChunk
            ) {
              callbacks.onChunk(payload.content)
            } else if (payload.type === 'done') {
              if (payload.ok && callbacks.onDone)
                callbacks.onDone(payload.usage || {})
              else if (!payload.ok && callbacks.onError)
                callbacks.onError(payload.detail || 'Unknown error')
            }
          } catch (parseError) {
            void parseError
          }
        }
      }
      if (buffer.trim()) {
        const line = buffer.split('\n').find((l) => l.startsWith('data:'))
        if (line) {
          try {
            const payload = JSON.parse(line.slice(5).trim())
            if (payload.type === 'done' && payload.ok && callbacks.onDone)
              callbacks.onDone(payload.usage || {})
            else if (
              payload.type === 'done' &&
              !payload.ok &&
              callbacks.onError
            )
              callbacks.onError(payload.detail || 'Unknown error')
          } catch (parseError) {
            void parseError
          }
        }
      }
    } catch (readErr) {
      if (readErr?.name === 'AbortError' && callbacks.onError) {
        callbacks.onError('aborted')
      } else {
        throw readErr
      }
    }
  },

  getLLMConfigUsers(params = {}) {
    return apiClient
      .get('/v1/admin/llm-config/users/', { params })
      .then(extractData)
  },
  getLLMConfigUser(userId) {
    return apiClient
      .get(`/v1/admin/llm-config/users/${encodeURIComponent(userId)}/`)
      .then(extractData)
  },
  putLLMConfigUser(userId, body) {
    return apiClient
      .put(`/v1/admin/llm-config/users/${encodeURIComponent(userId)}/`, body)
      .then(extractData)
  },
  deleteLLMConfigUser(userId) {
    return apiClient.delete(
      `/v1/admin/llm-config/users/${encodeURIComponent(userId)}/`
    )
  },
  getUsers(params = {}) {
    return apiClient.get('/v1/admin/users/', { params }).then(extractData)
  }
}
