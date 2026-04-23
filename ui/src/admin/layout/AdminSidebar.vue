<template>
  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-150"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="showMobileMenu && isMobile"
      @click="$emit('close')"
      class="layout-admin-overlay fixed inset-0 bg-gray-900 bg-opacity-50 z-40 lg:hidden"
    />
  </Transition>

  <aside
    :class="[
      'layout-admin-sidebar bg-slate-800/95 border-r border-slate-700 flex flex-col transition-transform duration-300 ease-in-out w-64 flex-shrink-0 h-full',
      isMobile ? 'fixed inset-y-0 left-0 z-50' : 'static',
      isMobile && !showMobileMenu ? '-translate-x-full' : 'translate-x-0'
    ]"
  >
    <div
      class="flex items-center justify-between h-16 px-4 border-b border-slate-700"
    >
      <router-link
        to="/management"
        class="flex items-center space-x-2 flex-1"
        @click="isMobile && $emit('close')"
      >
        <img
          src="/android-chrome-192x192.png"
          alt="AIMYChats Admin"
          class="w-8 h-8"
        />
        <span class="text-xl font-semibold text-slate-100">{{
          t('management.logoTitle')
        }}</span>
      </router-link>
      <button
        v-if="isMobile"
        @click="$emit('close')"
        class="p-2 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-700"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto flex flex-col">
      <div class="flex-1 space-y-1">
        <div class="menu-group">
          <button
            @click="toggleThreadlineMenu"
            class="admin-nav-item admin-nav-item-parent w-full"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12h6m-6 4h6M4 6h16M4 18h16"
              />
            </svg>
            <span class="flex-1 text-left">{{
              t('threadline.menuTitle')
            }}</span>
            <svg
              class="w-4 h-4 transition-transform"
              :class="threadlineMenuOpen ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-96"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 max-h-96"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="threadlineMenuOpen" class="submenu">
              <router-link
                to="/management/threadline/config"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/threadline/config')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/threadline/config')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                </svg>
                <span>{{ t('threadline.config.menuTitle') }}</span>
              </router-link>
              <router-link
                to="/management/threadline/periodic-tasks"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/threadline/periodic-tasks')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="
                  preloadRoute('/management/threadline/periodic-tasks')
                "
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{{ t('threadline.periodicTasks.menuTitle') }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <div class="menu-group">
          <button
            @click="toggleUserManagementMenu"
            class="admin-nav-item admin-nav-item-parent w-full"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
            <span class="flex-1 text-left">{{
              t('management.userManagement')
            }}</span>
            <svg
              class="w-4 h-4 transition-transform"
              :class="userManagementMenuOpen ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-96"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 max-h-96"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="userManagementMenuOpen" class="submenu">
              <router-link
                to="/management/users"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/users') ? 'admin-nav-item-active' : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/users')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                <span>{{ t('management.userManagement') }}</span>
              </router-link>
              <router-link
                to="/management/groups"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/groups') ? 'admin-nav-item-active' : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/groups')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                <span>{{ t('management.groupManagement') }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <div class="menu-group">
          <button
            @click="toggleLLMMenu"
            class="admin-nav-item admin-nav-item-parent w-full"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            <span class="flex-1 text-left">{{ t('llm.menuTitle') }}</span>
            <svg
              class="w-4 h-4 transition-transform"
              :class="llmMenuOpen ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-96"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 max-h-96"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="llmMenuOpen" class="submenu">
              <router-link
                to="/management/llm/stats"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/llm/stats')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/llm/stats')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                <span>{{ t('llm.stats.title') }}</span>
              </router-link>
              <router-link
                to="/management/llm/usage"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/llm/usage')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/llm/usage')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                  />
                </svg>
                <span>{{ t('llm.usage.title') }}</span>
              </router-link>
              <router-link
                to="/management/llm/config"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/llm/config')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/llm/config')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                </svg>
                <span>{{ t('llm.config.title') }}</span>
              </router-link>
              <router-link
                to="/management/llm/data-settings"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/llm/data-settings')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/llm/data-settings')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{{ t('llm.dataSettings.title') }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <div class="menu-group">
          <button
            @click="toggleTaskManagementMenu"
            class="admin-nav-item admin-nav-item-parent w-full"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
              />
            </svg>
            <span class="flex-1 text-left">{{
              t('taskManagement.menuTitle')
            }}</span>
            <svg
              class="w-4 h-4 transition-transform"
              :class="taskManagementMenuOpen ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-96"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 max-h-96"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="taskManagementMenuOpen" class="submenu">
              <router-link
                to="/management/task-management/stats"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/task-management/stats')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/task-management/stats')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                <span>{{ t('taskManagement.stats.title') }}</span>
              </router-link>
              <router-link
                to="/management/task-management/list"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/task-management/list')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/task-management/list')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 6h16M4 10h16M4 14h16M4 18h16"
                  />
                </svg>
                <span>{{ t('taskManagement.list.title') }}</span>
              </router-link>
              <router-link
                to="/management/task-management/settings"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/task-management/settings')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="
                  preloadRoute('/management/task-management/settings')
                "
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                </svg>
                <span>{{ t('taskManagement.settings.title') }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <div class="menu-group">
          <button
            @click="toggleNotificationManagementMenu"
            class="admin-nav-item admin-nav-item-parent w-full"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <span class="flex-1 text-left">{{
              t('notificationManagement.menuTitle')
            }}</span>
            <svg
              class="w-4 h-4 transition-transform"
              :class="notificationManagementMenuOpen ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 max-h-0"
            enter-to-class="opacity-100 max-h-96"
            leave-active-class="transition-all duration-200 ease-in"
            leave-from-class="opacity-100 max-h-96"
            leave-to-class="opacity-0 max-h-0"
          >
            <div v-if="notificationManagementMenuOpen" class="submenu">
              <router-link
                to="/management/notifier/stats"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/notifier/stats')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/notifier/stats')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                <span>{{ t('notificationManagement.stats.title') }}</span>
              </router-link>
              <router-link
                to="/management/notifier/records"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/notifier/records')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/notifier/records')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 6h16M4 10h16M4 14h16M4 18h16"
                  />
                </svg>
                <span>{{ t('notificationManagement.records.title') }}</span>
              </router-link>
              <router-link
                to="/management/notifier/channels"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/notifier/channels')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/notifier/channels')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span>{{
                  t('notificationManagement.channels.menuTitle')
                }}</span>
              </router-link>
              <router-link
                to="/management/notifier/settings"
                class="admin-nav-item admin-nav-item-child"
                :class="
                  isActive('/management/notifier/settings')
                    ? 'admin-nav-item-active'
                    : ''
                "
                @click="isMobile && $emit('close')"
                @mouseenter="preloadRoute('/management/notifier/settings')"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span>{{
                  t('notificationManagement.settings.menuTitle')
                }}</span>
              </router-link>
            </div>
          </Transition>
        </div>
      </div>

      <div class="mt-auto pt-4 border-t border-slate-700">
        <router-link
          to="/dashboard"
          class="admin-nav-item"
          @click="isMobile && $emit('close')"
          @mouseenter="preloadRoute('/dashboard')"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          <span>{{ t('management.backToUserPlatform') }}</span>
        </router-link>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps({
  showMobileMenu: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const userManagementMenuOpen = ref(true)
const llmMenuOpen = ref(true)
const threadlineMenuOpen = ref(true)
const taskManagementMenuOpen = ref(true)
const notificationManagementMenuOpen = ref(true)

const MOBILE_BREAKPOINT = 1024
const isMobile = computed(() => {
  if (typeof window === 'undefined') return false
  return window.innerWidth < MOBILE_BREAKPOINT
})

const isActive = (path) => {
  return route.path === path || route.path.startsWith(path + '/')
}

const toggleUserManagementMenu = () => {
  userManagementMenuOpen.value = !userManagementMenuOpen.value
}

const toggleLLMMenu = () => {
  llmMenuOpen.value = !llmMenuOpen.value
}

const toggleThreadlineMenu = () => {
  threadlineMenuOpen.value = !threadlineMenuOpen.value
}

const toggleTaskManagementMenu = () => {
  taskManagementMenuOpen.value = !taskManagementMenuOpen.value
}

const toggleNotificationManagementMenu = () => {
  notificationManagementMenuOpen.value = !notificationManagementMenuOpen.value
}

watch(
  () => route.path,
  (newPath) => {
    if (
      newPath.startsWith('/management/users') ||
      newPath.startsWith('/management/groups')
    )
      userManagementMenuOpen.value = true
    if (newPath.startsWith('/management/llm')) llmMenuOpen.value = true
    if (newPath.startsWith('/management/threadline'))
      threadlineMenuOpen.value = true
    if (newPath.startsWith('/management/task-management'))
      taskManagementMenuOpen.value = true
    if (newPath.startsWith('/management/notifier'))
      notificationManagementMenuOpen.value = true
  },
  { immediate: true }
)

const preloadCache = new Set()
const preloadRoute = (path) => {
  if (preloadCache.has(path)) return
  try {
    const r = router.resolve(path)
    if (r.matched.length > 0 && r.matched[0].components) {
      Object.values(r.matched[0].components).forEach((component) => {
        if (typeof component === 'function') {
          preloadCache.add(path)
          component().catch(() => preloadCache.delete(path))
        }
      })
    }
  } catch (err) {
    void err
  }
}
</script>

<style scoped>
.admin-nav-item {
  @apply flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-slate-100 transition-all duration-200;
}

.admin-nav-item-active {
  @apply bg-indigo-500/90 text-white hover:bg-indigo-500/90 hover:text-white;
}

.admin-nav-item-parent {
  @apply w-full cursor-pointer font-semibold text-slate-200;
}

.admin-nav-item-parent:hover {
  @apply bg-slate-700 text-slate-100;
}

.admin-nav-item-child {
  @apply relative pl-10 py-2 text-sm font-normal text-slate-400;
  margin-left: 0.75rem;
  border-radius: 0.375rem;
}

.admin-nav-item-child:hover {
  @apply bg-slate-700 text-slate-200;
}

.admin-nav-item-child.admin-nav-item-active {
  @apply bg-indigo-500/80 text-white font-medium;
}

.menu-group {
  @apply space-y-0 mb-1.5;
}

.submenu {
  @apply overflow-hidden pl-0 mt-1 space-y-0.5;
  transition: all 0.2s ease-in-out;
}

.submenu .admin-nav-item {
  @apply ml-0;
}

.admin-nav-item-child::before {
  content: '';
  @apply absolute left-6 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-slate-600 rounded;
}

.admin-nav-item-child.admin-nav-item-active::before {
  @apply bg-indigo-400 w-1;
}

.admin-nav-item-parent svg:first-child,
.admin-nav-item-parent span {
  @apply flex-shrink-0;
}

.admin-nav-item-parent svg:last-child {
  @apply flex-shrink-0 ml-1 opacity-70;
  transition:
    transform 0.2s ease-in-out,
    opacity 0.2s;
}

.admin-nav-item-parent:hover svg:last-child {
  @apply opacity-100;
}
</style>
