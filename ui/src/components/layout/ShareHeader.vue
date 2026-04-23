<template>
  <header class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo and title -->
        <div class="flex items-center gap-3">
          <router-link to="/chats" class="flex items-center space-x-2">
            <img
              src="/android-chrome-192x192.png"
              alt="AImyChats Logo"
              class="w-8 h-8"
            />
            <span class="text-xl font-semibold text-gray-900">{{
              t('common.appName')
            }}</span>
          </router-link>
        </div>

        <!-- Language Switcher -->
        <div class="flex items-center">
          <LanguageSwitcher />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'

const { t } = useI18n()
</script>
