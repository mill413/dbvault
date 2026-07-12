<template>
  <el-container class="layout-container">
    <el-aside width="260px" class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><Coin /></el-icon>
        <h2>DBVault</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        background-color="transparent"
        text-color="var(--sidebar-text)"
        active-text-color="var(--sidebar-active-text)"
      >
        <el-menu-item v-if="canView('Dashboard')" index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>{{ $t('common.dashboard') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Databases')" index="/databases">
          <el-icon><Coin /></el-icon>
          <span>{{ $t('common.databases') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('DatabaseBrowser')" index="/database-browser">
          <el-icon><Grid /></el-icon>
          <span>{{ $t('common.databaseBrowser') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Storages')" index="/storages">
          <el-icon><Files /></el-icon>
          <span>{{ $t('common.storage') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Backups')" index="/backups">
          <el-icon><Upload /></el-icon>
          <span>{{ $t('common.backups') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Jobs')" index="/jobs">
          <el-icon><Clock /></el-icon>
          <span>{{ $t('common.schedules') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Audit')" index="/audit">
          <el-icon><Document /></el-icon>
          <span>{{ $t('common.auditLogs') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Restores')" index="/restores">
          <el-icon><Download /></el-icon>
          <span>{{ $t('common.restores') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Alerts')" index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>{{ $t('common.alerts') }}</span>
        </el-menu-item>
        <el-menu-item v-if="canView('Users')" index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>{{ $t('common.users') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <el-switch
            v-model="isDark"
            inline-prompt
            :active-icon="Moon"
            :inactive-icon="Sunny"
            @change="toggleDark"
            style="margin-right: 24px; --el-switch-on-color: var(--border-color); --el-switch-off-color: var(--border-color);"
          />
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-profile">
              <div class="avatar">
                <el-icon><User /></el-icon>
              </div>
              <div class="user-details">
                <span class="username">{{ authStore.user?.username || 'User' }}</span>
                <span class="role">{{ authStore.user?.role || 'Guest' }}</span>
              </div>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">{{ $t('common.signOut') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { canViewRoute } from '../utils/permissions'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')
const userRole = computed(() => authStore.user?.role || '')
const canView = (name) => canViewRoute(userRole.value, name)

const isDark = ref(localStorage.getItem('theme') === 'dark')

const toggleDark = (val) => {
  if (val) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
  }
}

onMounted(() => {
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  }

  if (route.query.denied === '1') {
    ElMessage.warning(t('common.accessDenied'))
    router.replace({ path: route.path, query: {} })
  }
})

const handleCommand = async (command) => {
  if (command === 'logout') {
    await authStore.logout()
    ElMessage.success(t('common.signOut') + ' OK')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background-color: var(--main-bg);
}

.sidebar {
  background-color: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 10px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.logo {
  height: 80px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  color: white;
}

.logo-icon {
  font-size: 28px;
  color: var(--el-color-primary);
}

.logo h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.sidebar-menu {
  border-right: none;
  padding: 10px;
}

.sidebar-menu .el-menu-item {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 48px;
  line-height: 48px;
  font-weight: 500;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: var(--sidebar-active-bg) !important;
  color: var(--sidebar-active-text) !important;
}

.sidebar-menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

.header {
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
  height: 70px !important;
  z-index: 5;
}

.header-left .page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-color);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-profile:hover {
  background: var(--bg-color-mute);
}

.avatar {
  width: 36px;
  height: 36px;
  background: var(--bg-color-mute);
  color: var(--el-color-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-color);
}

.role {
  font-size: 12px;
  color: var(--text-muted);
}

.dropdown-icon {
  color: var(--text-muted);
  font-size: 12px;
}

.main-content {
  padding: 30px;
  overflow-y: auto;
  position: relative;
}

/* Page Transitions */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateY(15px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateY(-15px);
}
</style>
