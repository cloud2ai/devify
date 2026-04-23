<template>
  <div class="layout-admin h-screen flex w-full overflow-hidden bg-gray-50">
    <AdminSidebar
      :show-mobile-menu="showMobileMenu"
      @close="showMobileMenu = false"
    />
    <div class="flex-1 flex flex-col min-w-0 w-0 h-full overflow-hidden">
      <AdminHeader @toggle-menu="showMobileMenu = !showMobileMenu" />
      <main class="flex-1 py-3 px-4 min-w-0 overflow-y-auto bg-gray-50">
        <div :key="route.path">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import AdminHeader from './AdminHeader.vue'
import AdminSidebar from './AdminSidebar.vue'

const showMobileMenu = ref(false)
const route = useRoute()
</script>
