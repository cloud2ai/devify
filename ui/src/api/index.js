import axios from 'axios'
import apiConfig from '@/config/api'

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

const api = axios.create({
  baseURL: apiConfig.apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

let refreshTokenPromise = null

function isAuthEndpoint(url = '') {
  return (
    url.includes('/v1/auth/login') ||
    url.includes('/v1/auth/logout') ||
    url.includes('/v1/auth/token/refresh') ||
    url.includes('/v1/auth/registration') ||
    url.includes('/v1/auth/register/') ||
    url.includes('/v1/auth/oauth/')
  )
}

function extractResponseData(response) {
  const body = response?.data
  if (body && typeof body === 'object' && 'data' in body) {
    return body.data
  }
  return body
}

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    if (!originalRequest || !error.response) {
      return Promise.reject(error)
    }

    if (isAuthEndpoint(originalRequest.url)) {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          if (!refreshTokenPromise) {
            refreshTokenPromise = api
              .post('/v1/auth/token/refresh', {
                refresh: refreshToken
              })
              .then(extractResponseData)
              .finally(() => {
                refreshTokenPromise = null
              })
          }

          const refreshResponse = await refreshTokenPromise
          const newAccessToken = refreshResponse?.access

          if (!newAccessToken) {
            throw new Error('Refresh token response did not include access')
          }

          localStorage.setItem('access_token', newAccessToken)

          // Retry original request with new token
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        // No refresh token, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

export default api
