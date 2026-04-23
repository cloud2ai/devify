/**
 * Admin (management) routes. Mount with ...adminRoutes in the main router (before 404/catch-all).
 */
export const adminRoutes = [
  {
    path: '/management',
    redirect: '/management/users'
  },
  {
    path: '/management/users',
    name: 'ManagementUsers',
    component: () => import('@/admin/pages/Management/Users.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/groups',
    name: 'ManagementGroups',
    component: () => import('@/admin/pages/Management/Groups.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/llm',
    redirect: '/management/llm/stats'
  },
  {
    path: '/management/llm/stats',
    name: 'LLMStats',
    component: () => import('@/admin/pages/LLM/Stats.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/llm/usage',
    name: 'LLMUsage',
    component: () => import('@/admin/pages/LLM/Usage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/llm/config',
    name: 'LLMConfig',
    component: () => import('@/admin/pages/LLM/Config.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/llm/data-settings',
    name: 'LLMDataSettings',
    component: () => import('@/admin/pages/LLM/DataSettings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/threadline',
    redirect: '/management/threadline/config'
  },
  {
    path: '/management/threadline/config',
    name: 'ThreadlineConfig',
    component: () => import('@/admin/pages/Threadline/Config.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/threadline/periodic-tasks',
    name: 'ThreadlinePeriodicTasks',
    component: () => import('@/admin/pages/Threadline/PeriodicTasks.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/task-management',
    redirect: '/management/task-management/list'
  },
  {
    path: '/management/task-management/list',
    name: 'TaskManagementList',
    component: () => import('@/admin/pages/TaskManagement/List.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/task-management/stats',
    name: 'TaskManagementStats',
    component: () => import('@/admin/pages/TaskManagement/Stats.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/task-management/settings',
    name: 'TaskManagementSettings',
    component: () => import('@/admin/pages/TaskManagement/Settings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/notifier',
    redirect: '/management/notifier/stats'
  },
  {
    path: '/management/notifier/stats',
    name: 'AdminNotificationsStats',
    component: () => import('@/admin/pages/Notifications/Stats.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/notifier/records',
    name: 'AdminNotificationsRecords',
    component: () => import('@/admin/pages/Notifications/Records.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/notifier/channels',
    name: 'AdminNotificationsChannels',
    component: () => import('@/admin/pages/Notifications/Channels.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/notifier/settings',
    name: 'AdminNotificationsSettings',
    component: () => import('@/admin/pages/Notifications/Config.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/management/notifier/config',
    redirect: '/management/notifier/settings'
  }
]
