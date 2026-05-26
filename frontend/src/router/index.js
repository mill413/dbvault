import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
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
        meta: { title: '仪表盘' },
      },
      {
        path: 'databases',
        name: 'Databases',
        component: () => import('../views/Databases.vue'),
        meta: { title: '数据库实例' },
      },
      {
        path: 'storages',
        name: 'Storages',
        component: () => import('../views/Storages.vue'),
        meta: { title: '存储管理' },
      },
      {
        path: 'backups',
        name: 'Backups',
        component: () => import('../views/Backups.vue'),
        meta: { title: '备份管理' },
      },
      {
        path: 'jobs',
        name: 'Jobs',
        component: () => import('../views/Jobs.vue'),
        meta: { title: '定时任务' },
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('../views/Audit.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'restores',
        name: 'Restores',
        component: () => import('../views/Restores.vue'),
        meta: { title: '恢复管理' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('../views/Alerts.vue'),
        meta: { title: '告警管理' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理' },
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
  }

  if (to.path === '/login' && authStore.accessToken) {
    return next('/')
  }

  next()
})

export default router
