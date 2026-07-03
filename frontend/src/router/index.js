import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { canViewRoute } from '../utils/permissions'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { titleKey: 'common.dashboard' },
      },
      {
        path: 'databases',
        name: 'Databases',
        component: () => import('../views/Databases.vue'),
        meta: { titleKey: 'common.databases' },
      },
      {
        path: 'storages',
        name: 'Storages',
        component: () => import('../views/Storages.vue'),
        meta: { titleKey: 'common.storage' },
      },
      {
        path: 'backups',
        name: 'Backups',
        component: () => import('../views/Backups.vue'),
        meta: { titleKey: 'common.backups' },
      },
      {
        path: 'jobs',
        name: 'Jobs',
        component: () => import('../views/Jobs.vue'),
        meta: { titleKey: 'common.schedules' },
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('../views/Audit.vue'),
        meta: { titleKey: 'common.auditLogs' },
      },
      {
        path: 'restores',
        name: 'Restores',
        component: () => import('../views/Restores.vue'),
        meta: { titleKey: 'common.restores' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('../views/Alerts.vue'),
        meta: { titleKey: 'common.alerts' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { titleKey: 'common.users' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false) {
    if (!authStore.accessToken) {
      return next('/login')
    }
    if (!authStore.user) {
      await authStore.fetchUser()
      if (!authStore.user) {
        return next('/login')
      }
    }

    const role = authStore.user?.role
    if (role && !canViewRoute(role, to.name)) {
      return next({ path: '/dashboard', query: { denied: '1' } })
    }
  }

  if (to.path === '/login' && authStore.accessToken) {
    return next('/')
  }

  next()
})

export default router
