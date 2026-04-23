<template>
  <AppLayout>
    <div
      class="not-found-wrapper min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-12"
    >
      <div class="max-w-2xl mx-auto px-6 py-12 text-center relative">
        <!-- Floating particles animation -->
        <div class="absolute inset-0 overflow-hidden pointer-events-none">
          <div
            v-for="(pos, i) in particlePositions"
            :key="i"
            class="particle absolute rounded-full"
            :style="pos"
          ></div>
        </div>

        <!-- Main content -->
        <div class="relative z-10">
          <!-- 404 Number with style -->
          <div class="mb-8">
            <h1
              class="text-8xl md:text-9xl font-light text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 tracking-tight"
            >
              {{ t('notFound.title') }}
            </h1>
          </div>

          <!-- Philosophical quote -->
          <div class="mb-8 space-y-6">
            <div
              class="text-2xl md:text-3xl font-light text-gray-700 italic leading-relaxed"
            >
              <p class="mb-4">"{{ t('notFound.quote') }}"</p>
            </div>

            <div class="text-lg md:text-xl text-gray-500 font-light">
              <p>
                {{ t('notFound.description') }}
              </p>
            </div>
          </div>

          <!-- Decorative line -->
          <div class="flex items-center justify-center gap-4 mb-8">
            <div
              class="h-px w-16 bg-gradient-to-r from-transparent via-blue-400 to-transparent"
            ></div>
            <div class="w-2 h-2 rounded-full bg-blue-400"></div>
            <div
              class="h-px w-16 bg-gradient-to-r from-transparent via-purple-400 to-transparent"
            ></div>
          </div>

          <!-- Navigation buttons -->
          <div
            class="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <BaseButton
              @click="goHome"
              variant="primary"
              class="group relative px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-medium transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/50 hover:scale-105 transform"
            >
              {{ t('notFound.returnHome') }}
              <svg
                class="inline-block ml-2 w-5 h-5 transform transition-transform group-hover:translate-x-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </BaseButton>

            <BaseButton
              @click="goBack"
              variant="outline"
              class="px-8 py-3 border-2 border-gray-300 text-gray-700 rounded-full font-medium transition-all duration-300 hover:bg-gray-100 hover:border-gray-400"
            >
              {{ t('notFound.goBack') }}
            </BaseButton>
          </div>

          <!-- Additional philosophical note -->
          <div class="mt-12 pt-8 border-t border-gray-200">
            <p class="text-sm text-gray-400 italic">
              {{ t('notFound.philosophy') }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()
const { t } = useI18n()

const goHome = () => {
  router.push('/dashboard')
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}

const particlePositions = ref([])

onMounted(() => {
  const positions = []
  for (let i = 0; i < 12; i++) {
    const size = 20 + Math.random() * 40
    const left = Math.random() * 100
    const top = Math.random() * 100
    const delay = Math.random() * 5
    const duration = 10 + Math.random() * 10
    const color1 = Math.floor(99 + Math.random() * 100)
    const color2 = Math.floor(102 + Math.random() * 100)
    const color3 = Math.floor(141 + Math.random() * 100)

    positions.push({
      width: `${size}px`,
      height: `${size}px`,
      left: `${left}%`,
      top: `${top}%`,
      background: `radial-gradient(circle,
        rgba(${color1}, ${color2}, ${color3}, 0.3),
        rgba(${color1}, ${color2}, ${color3}, 0)
      )`,
      '--delay': `${delay}s`,
      '--duration': `${duration}s`
    })
  }
  particlePositions.value = positions
})
</script>

<style scoped>
.not-found-wrapper {
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue',
    Arial, sans-serif;
}

/* Smooth fade in */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.not-found-wrapper > div {
  animation: fadeIn 0.8s ease-out;
}

.particle {
  animation: float var(--duration, 15s) ease-in-out var(--delay, 0s) infinite
    alternate;
}

@keyframes float {
  0% {
    transform: translateY(0) translateX(0) rotate(0deg);
    opacity: 0.2;
  }
  50% {
    opacity: 0.4;
  }
  100% {
    transform: translateY(-30px) translateX(20px) rotate(180deg);
    opacity: 0.1;
  }
}
</style>
