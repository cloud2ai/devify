/**
 * Accessibility utility functions
 */

/**
 * Generate unique ID for accessibility
 * @param {string} prefix - Prefix for the ID
 * @returns {string} - Unique ID
 */
export function generateId(prefix = 'id') {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Check if element is focusable
 * @param {HTMLElement} element - Element to check
 * @returns {boolean} - Whether element is focusable
 */
export function isFocusable(element) {
  if (!element) return false

  const focusableSelectors = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    'area[href]',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]'
  ]

  return focusableSelectors.some((selector) => element.matches(selector))
}

/**
 * Get all focusable elements within a container
 * @param {HTMLElement} container - Container element
 * @returns {HTMLElement[]} - Array of focusable elements
 */
export function getFocusableElements(container) {
  if (!container) return []

  const focusableSelectors = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    'area[href]',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]'
  ].join(', ')

  return Array.from(container.querySelectorAll(focusableSelectors))
}

/**
 * Trap focus within a container
 * @param {HTMLElement} container - Container to trap focus in
 * @param {HTMLElement} firstFocusable - First focusable element
 * @param {HTMLElement} lastFocusable - Last focusable element
 */
export function trapFocus(container, firstFocusable, lastFocusable) {
  const handleTabKey = (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          lastFocusable.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastFocusable) {
          firstFocusable.focus()
          e.preventDefault()
        }
      }
    }
  }

  container.addEventListener('keydown', handleTabKey)

  return () => {
    container.removeEventListener('keydown', handleTabKey)
  }
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 * @param {string} priority - Priority level ('polite' or 'assertive')
 */
export function announceToScreenReader(message, priority = 'polite') {
  const announcement = document.createElement('div')
  announcement.setAttribute('aria-live', priority)
  announcement.setAttribute('aria-atomic', 'true')
  announcement.className = 'sr-only'
  announcement.textContent = message

  document.body.appendChild(announcement)

  setTimeout(() => {
    document.body.removeChild(announcement)
  }, 1000)
}

/**
 * Get ARIA label for loading state
 * @param {boolean} loading - Whether component is loading
 * @param {string} action - Action being performed
 * @returns {string} - ARIA label
 */
export function getLoadingAriaLabel(loading, action = 'Loading') {
  return loading ? `${action}...` : action
}

/**
 * Validate ARIA attributes
 * @param {Object} attributes - ARIA attributes to validate
 * @returns {Object} - Validated attributes
 */
export function validateAriaAttributes(attributes) {
  const validAttributes = {}

  Object.entries(attributes).forEach(([key, value]) => {
    if (key.startsWith('aria-') && value !== null && value !== undefined) {
      validAttributes[key] = value
    }
  })

  return validAttributes
}
