<template>
  <div class="login-container">
    <div class="login-left">
      <div class="brand">
        <el-icon class="brand-icon"><Coin /></el-icon>
        <h2>DBVault</h2>
      </div>
      <div class="slogan">
        <h1>{{ $t('login.title') }}</h1>
        <p>{{ $t('login.subtitle') }}</p>
      </div>
    </div>
    <div class="login-right">
      <div class="login-card">
        <div class="login-header">
          <h2>{{ $t('login.welcome') }}</h2>
          <p>{{ $t('login.prompt') }}</p>
        </div>
        <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleLogin" size="large">
          <el-form-item prop="username">
            <el-input v-model="form.username" :placeholder="$t('login.username')" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              :placeholder="$t('login.password')"
              prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleLogin" class="submit-btn">
              {{ $t('login.signIn') }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const { t } = useI18n()

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: t('login.username'), trigger: 'blur' }],
  password: [{ required: true, message: t('login.password'), trigger: 'blur' }],
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success(t('login.success'))
    router.push('/')
  } catch (error) {
    console.error('Login failed:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  min-height: 100vh;
  background-color: var(--main-bg);
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #1e1e2d 0%, #151521 100%);
  color: white;
  padding: 60px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.login-left::after {
  content: '';
  position: absolute;
  top: -20%;
  right: -20%;
  width: 60%;
  height: 60%;
  background: radial-gradient(circle, rgba(0, 210, 255, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
  border-radius: 50%;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
  z-index: 1;
}

.brand-icon {
  font-size: 32px;
}

.slogan {
  z-index: 1;
  margin-bottom: 100px;
}

.slogan h1 {
  font-size: 48px;
  line-height: 1.2;
  margin-bottom: 20px;
  font-weight: 800;
}

.slogan p {
  font-size: 18px;
  color: #a1a5b7;
  max-width: 400px;
  line-height: 1.6;
}

.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
}

.login-header {
  margin-bottom: 40px;
}

.login-header h2 {
  font-size: 32px;
  color: #181c32;
  margin: 0 0 10px;
  font-weight: 700;
}

.login-header p {
  color: #a1a5b7;
  margin: 0;
  font-size: 15px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-top: 10px;
}

:deep(.el-input__wrapper) {
  background-color: #f5f8fa;
  border: none;
  box-shadow: none !important;
  border-radius: 8px;
  padding: 0 16px;
}

:deep(.el-input__wrapper.is-focus) {
  background-color: #eef3f7;
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

:deep(.el-input__inner) {
  height: 48px;
}
</style>
