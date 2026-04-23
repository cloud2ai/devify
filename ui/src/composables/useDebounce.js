import { ref, watch } from 'vue'

/**
 * Debounce composable for performance optimization
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Object} - { debouncedFn, cancel }
 */
export function useDebounce(fn, delay = 300) {
  const timeoutId = ref(null)

  const debouncedFn = (...args) => {
    if (timeoutId.value) {
      clearTimeout(timeoutId.value)
    }

    timeoutId.value = setTimeout(() => {
      fn(...args)
    }, delay)
  }

  const cancel = () => {
    if (timeoutId.value) {
      clearTimeout(timeoutId.value)
      timeoutId.value = null
    }
  }

  return {
    debouncedFn,
    cancel
  }
}

/**
 * Throttle composable for performance optimization
 * @param {Function} fn - Function to throttle
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Throttled function
 */
export function useThrottle(fn, delay = 300) {
  const lastCall = ref(0)

  return (...args) => {
    const now = Date.now()

    if (now - lastCall.value >= delay) {
      lastCall.value = now
      fn(...args)
    }
  }
}

/**
 * Intersection Observer composable for lazy loading
 * @param {Object} options - Intersection Observer options
 * @returns {Object} - { isIntersecting, targetRef, observer }
 */
export function useIntersectionObserver(options = {}) {
  const isIntersecting = ref(false)
  const targetRef = ref(null)
  const observer = ref(null)

  const observe = () => {
    if (targetRef.value && !observer.value) {
      observer.value = new IntersectionObserver(
        ([entry]) => {
          isIntersecting.value = entry.isIntersecting
        },
        {
          threshold: 0.1,
          ...options
        }
      )

      observer.value.observe(targetRef.value)
    }
  }

  const disconnect = () => {
    if (observer.value) {
      observer.value.disconnect()
      observer.value = null
    }
  }

  return {
    isIntersecting,
    targetRef,
    observer,
    observe,
    disconnect
  }
}
