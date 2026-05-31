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
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/databases">
          <el-icon><Coin /></el-icon>
          <span>Databases</span>
        </el-menu-item>
        <el-menu-item index="/storages">
          <el-icon><Files /></el-icon>
          <span>Storage</span>
        </el-menu-item>
        <el-menu-item index="/backups">
          <el-icon><Upload /></el-icon>
          <span>Backups</span>
        </el-menu-item>
        <el-menu-item index="/jobs">
          <el-icon><Clock /></el-icon>
          <span>Schedules</span>
        </el-menu-item>
        <el-menu-item index="/audit">
          <el-icon><Document /></el-icon>
          <span>Audit Logs</span>
        </el-menu-item>
        <el-menu-item index="/restores">
          <el-icon><Download /></el-icon>
          <span>Restores</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>Alerts</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>Users</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
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
                <el-dropdown-item command="logout">Sign Out</el-dropdown-item>
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')

const handleCommand = async (command) => {
  if (command === 'logout') {
    await authStore.logout()
    ElMessage.success('Signed out successfully')
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
  background: white;
  border-bottom: 1px solid #eff2f5;
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
  color: #181c32;
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
  background: #f5f8fa;
}

.avatar {
  width: 36px;
  height: 36px;
  background: #eef3f7;
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
  color: #3f4254;
}

.role {
  font-size: 12px;
  color: #a1a5b7;
}

.dropdown-icon {
  color: #a1a5b7;
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
