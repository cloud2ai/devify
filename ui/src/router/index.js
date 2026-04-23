import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import { adminRoutes } from '@/admin'

const routes = [
  {
    path: '/',
    redirect: '/chats'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Auth.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/pages/Auth.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/register/complete/:token',
    name: 'RegisterComplete',
    component: () => import('@/pages/RegisterComplete.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/reset-password/:uid/:token',
    name: 'PasswordReset',
    component: () => import('@/pages/PasswordReset.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/auth/oauth/callback',
    name: 'OAuthCallback',
    component: () => import('@/pages/OAuthCallback.vue')
  },
  {
    path: '/auth/google/callback',
    redirect: '/auth/oauth/callback'
  },
  {
    path: '/auth/wechat/callback',
    redirect: '/auth/oauth/callback'
  },
  {
    path: '/google/complete-setup',
    name: 'GoogleCompleteSetup',
    component: () => import('@/pages/GoogleCompleteSetup.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chats',
    name: 'Chats',
    component: () => import('@/pages/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    redirect: '/chats'
  },
  {
    path: '/conversations',
    redirect: '/chats'
  },
  {
    path: '/chats/:id',
    name: 'ChatDetail',
    component: () => import('@/pages/ThreadlineDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/conversations/:id',
    redirect: (to) => `/chats/${to.params.id}`
  },
  {
    path: '/threadlines/:id',
    redirect: (to) => `/chats/${to.params.id}`
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/pages/Settings.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/todos',
    name: 'Todos',
    component: () => import('@/pages/TodosPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/billing',
    name: 'Billing',
    component: () => import('@/pages/Billing.vue'),
    meta: { requiresAuth: true }
  },
  ...adminRoutes,
  {
    path: '/chats/share/:token',
    name: 'ThreadlineShare',
    component: () => import('@/pages/ThreadlineShareView.vue')
  },
  {
    path: '/share/:token',
    redirect: (to) => `/chats/share/${to.params.token}`
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/pages/NotFound.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'CatchAll',
    component: () => import('@/pages/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAdmin) {
    if (!userStore.isAuthenticated) {
      const isValid = await userStore.checkAuth()
      if (!isValid) {
        next('/login')
        return
      }
    }
    if (!userStore.isAdmin) {
      next('/dashboard')
      return
    }
    next()
    return
  }

  // If route requires authentication
  if (to.meta.requiresAuth) {
    // If not currently authenticated, try to check auth from token
    if (!userStore.isAuthenticated) {
      const isValid = await userStore.checkAuth()
      if (!isValid) {
        next('/login')
        return
      }
    }
    next()
  } else if (to.meta.requiresGuest && userStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
