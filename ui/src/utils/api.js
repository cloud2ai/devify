/**
 * API Response Utilities
 *
 * Handles the unified response format from backend:
 * {
 *   "code": 0,
 *   "message": "success",
 *   "data": { ... }
 * }
 */

/**
 * Extract data from unified API response format
 * @param {Object} response - Axios response object
 * @returns {any} - The actual data from response
 */
export function extractResponseData(response) {
  // Handle unified response format: { code, message, data }
  if (
    response.data &&
    typeof response.data === 'object' &&
    'data' in response.data
  ) {
    return response.data.data
  }

  // Fallback to direct response data
  return response.data
}

/**
 * Extract error message from API error response
 * @param {Object} error - Axios error object
 * @param {string} defaultMessage - Default error message
 * @returns {string} - Error message
 */
export function extractErrorMessage(
  error,
  defaultMessage = 'An error occurred'
) {
  if (error.response?.data) {
    const data = error.response.data

    // Handle unified error format
    if (data.message) {
      return data.message
    }

    // Handle DRF error format
    if (data.detail) {
      return data.detail
    }

    // Handle validation errors
    if (data.non_field_errors && Array.isArray(data.non_field_errors)) {
      return data.non_field_errors[0]
    }

    // Handle field-specific errors
    const firstFieldError = Object.values(data).find(
      (value) => Array.isArray(value) && value.length > 0
    )
    if (firstFieldError) {
      return firstFieldError[0]
    }
  }

  return error.message || defaultMessage
}

/**
 * Check if API response indicates success
 * @param {Object} response - Axios response object
 * @returns {boolean} - Whether the response indicates success
 */
export function isApiSuccess(response) {
  // HTTP status check
  if (response.status < 200 || response.status >= 300) {
    return false
  }

  // Unified response format check
  if (
    response.data &&
    typeof response.data === 'object' &&
    'code' in response.data
  ) {
    return response.data.code === 0
  }

  return true
}
