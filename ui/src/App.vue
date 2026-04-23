<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <ErrorBoundary>
      <router-view />
    </ErrorBoundary>
    <Toast />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue'
import Toast from '@/components/ui/Toast.vue'

const userStore = useUserStore()

// Initialize app
onMounted(() => {
  // Check if user is logged in
  userStore.checkAuth()
})
</script>
