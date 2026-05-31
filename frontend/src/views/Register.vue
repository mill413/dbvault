<template>
  <div class="login-container">
    <div class="login-left">
      <div class="brand">
        <el-icon class="brand-icon"><Coin /></el-icon>
        <h2>DBVault</h2>
      </div>
      <div class="slogan">
        <h1>{{ $t('register.title') }}</h1>
        <p>{{ $t('register.subtitle') }}</p>
      </div>
    </div>
    <div class="login-right">
      <div class="login-card">
        <div class="login-header">
          <h2>{{ $t('register.title') }}</h2>
          <p>{{ $t('register.subtitle') }}</p>
        </div>
        <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleRegister" size="large" label-position="top">
          <el-form-item :label="$t('register.usernameLabel')" prop="username">
            <el-input v-model="form.username" :placeholder="$t('register.usernamePlaceholder')" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="display_name">
            <template #label>
              {{ $t('register.displayNameLabel') }}
              <span class="optional-tag">({{ $t('register.optional') }})</span>
            </template>
            <el-input v-model="form.display_name" :placeholder="$t('register.displayNamePlaceholder')" prefix-icon="UserFilled" />
          </el-form-item>
          <el-form-item prop="email">
            <template #label>
              {{ $t('register.emailLabel') }}
              <span class="optional-tag">({{ $t('register.optional') }})</span>
            </template>
            <el-input v-model="form.email" :placeholder="$t('register.emailPlaceholder')" prefix-icon="Message" />
          </el-form-item>
          <el-form-item :label="$t('register.passwordLabel')" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              :placeholder="$t('login.password')"
              prefix-icon="Lock"
              show-password
            />
            <div class="field-hint">
              <el-icon><InfoFilled /></el-icon>
              {{ $t('register.passwordHint') }}
            </div>
          </el-form-item>
          <el-form-item :label="$t('register.confirmPasswordLabel')" prop="confirmPassword">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              :placeholder="$t('register.confirmPasswordPlaceholder')"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleRegister" class="submit-btn">
              {{ $t('register.submit') }}
            </el-button>
          </el-form-item>
        </el-form>
        <div class="login-link">
          {{ $t('register.hasAccount') }}
          <router-link to="/login">{{ $t('register.backToLogin') }}</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { register, getPublicConfig } from '../api/auth'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { createPasswordValidator } from '../utils/validation'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const { t } = useI18n()

onMounted(async () => {
  try {
    const res = await getPublicConfig()
    if (!res.data.registration_enabled) {
      router.replace('/login')
    }
  } catch {
    router.replace('/login')
  }
})

const form = reactive({
  username: '',
  display_name: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error(t('register.passwordMismatch')))
  } else {
    callback()
  }
}

const rules = {
  username: [{ required: true, message: t('user.usernameRequired'), trigger: 'blur' }, { min: 3, max: 64, message: '3-64 characters', trigger: 'blur' }],
  password: [{ validator: createPasswordValidator(t), trigger: 'blur' }],
  confirmPassword: [{ required: true, message: t('user.passwordRequired'), trigger: 'blur' }, { validator: validateConfirmPassword, trigger: 'blur' }],
}

const handleRegister = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await register({
      username: form.username,
      password: form.password,
      display_name: form.display_name || null,
      email: form.email || null,
    })
    ElMessage.success(t('register.success'))
    router.push('/login')
  } catch (error) {
    console.error('Registration failed:', error)
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
  margin-bottom: 30px;
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

.login-link {
  text-align: center;
  margin-top: 20px;
  color: #a1a5b7;
  font-size: 14px;
}

.login-link a {
  color: var(--el-color-primary);
  text-decoration: none;
  font-weight: 600;
}

.login-link a:hover {
  text-decoration: underline;
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

.field-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1;
}

.optional-tag {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
  margin-left: 4px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
}
</style>
