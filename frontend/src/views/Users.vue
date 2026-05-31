<template>
  <div class="users">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('user.title') }}</span>
          <div class="header-filters">
            <el-input v-model="searchUsername" :placeholder="$t('user.searchUsername')" clearable style="width: 180px" />
            <el-select v-model="filterRole" :placeholder="$t('user.roleFilter')" clearable style="width: 130px">
              <el-option label="Admin" value="Admin" />
              <el-option label="Operator" value="Operator" />
              <el-option label="Viewer" value="Viewer" />
            </el-select>
            <el-select v-model="filterStatus" :placeholder="$t('user.statusFilter')" clearable style="width: 130px">
              <el-option label="ACTIVE" value="ACTIVE" />
              <el-option label="DISABLED" value="DISABLED" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              {{ $t('common.add') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredUsers" v-loading="loading" style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" :label="$t('login.username')" width="120" />
        <el-table-column prop="display_name" :label="$t('user.displayName')" width="150" />
        <el-table-column prop="email" :label="$t('user.email')" width="200" />
        <el-table-column prop="role" :label="$t('user.role')" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('user.lastLogin')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_login_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.createTime')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">{{ $t('common.edit') }}</el-button>
            <el-button size="small" type="warning" @click="showResetPasswordDialog(row)">{{ $t('user.resetPassword') }}</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="fetchData"
        @size-change="fetchData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('user.editUser') : $t('user.addUser')" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item :label="$t('login.username')" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" :placeholder="$t('user.usernamePlaceholder')" />
        </el-form-item>
        <el-form-item v-if="!isEdit" :label="$t('login.password')" prop="password">
          <el-input v-model="form.password" type="password" show-password :placeholder="$t('user.passwordLength')" />
        </el-form-item>
        <el-form-item :label="$t('user.displayName')" prop="display_name">
          <el-input v-model="form.display_name" :placeholder="$t('user.displayNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('user.email')" prop="email">
          <el-input v-model="form.email" :placeholder="$t('user.emailPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('user.role')" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="Admin" value="Admin" />
            <el-option label="Operator" value="Operator" />
            <el-option label="Viewer" value="Viewer" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEdit" :label="$t('common.status')" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="ACTIVE" value="ACTIVE" />
            <el-option label="DISABLED" value="DISABLED" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetPasswordVisible" :title="$t('user.resetPassword')" width="500px">
      <el-form :model="resetForm" :rules="resetRules" ref="resetFormRef" label-width="100px">
        <el-form-item :label="$t('common.users')">
          <el-input :value="currentUser?.username" disabled />
        </el-form-item>
        <el-form-item :label="$t('user.newPassword')" prop="password">
          <el-input v-model="resetForm.password" type="password" show-password :placeholder="$t('user.passwordLength')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPasswordVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="resetLoading">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser, resetPassword } from '../api/users'

const users = ref([])
const loading = ref(false)
const submitLoading = ref(false)
const resetLoading = ref(false)
const dialogVisible = ref(false)
const resetPasswordVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const resetFormRef = ref(null)
const currentUser = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchUsername = ref('')
const filterRole = ref('')
const filterStatus = ref('')
const { t } = useI18n()

const form = reactive({
  id: null,
  username: '',
  password: '',
  display_name: '',
  email: '',
  role: 'Viewer',
  status: 'ACTIVE',
})

const resetForm = reactive({
  password: '',
})

const rules = {
  username: [{ required: true, message: t('user.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('user.passwordRequired'), trigger: 'blur' }, { min: 12, message: t('user.passwordLength'), trigger: 'blur' }],
  role: [{ required: true, message: t('user.roleRequired'), trigger: 'change' }],
}

const resetRules = {
  password: [{ required: true, message: t('user.passwordRequired'), trigger: 'blur' }, { min: 12, message: t('user.passwordLength'), trigger: 'blur' }],
}

const getRoleType = (role) => {
  const map = { Admin: 'danger', Operator: 'warning', Viewer: 'info' }
  return map[role] || 'info'
}

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const filteredUsers = computed(() => {
  let result = users.value
  if (searchUsername.value) {
    const keyword = searchUsername.value.toLowerCase()
    result = result.filter((u) => (u.username || '').toLowerCase().includes(keyword))
  }
  if (filterRole.value) {
    result = result.filter((u) => u.role === filterRole.value)
  }
  if (filterStatus.value) {
    result = result.filter((u) => u.status === filterStatus.value)
  }
  return result
})

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getUsers({ page: page.value, page_size: pageSize.value })
    users.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  Object.assign(form, { id: null, username: '', password: '', display_name: '', email: '', role: 'Viewer', status: 'ACTIVE' })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  Object.assign(form, { ...row, password: '' })
  dialogVisible.value = true
}

const showResetPasswordDialog = (row) => {
  currentUser.value = row
  resetForm.password = ''
  resetPasswordVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateUser(form.id, {
        display_name: form.display_name,
        email: form.email,
        role: form.role,
        status: form.status,
      })
      ElMessage.success(t('common.updateSuccess'))
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        display_name: form.display_name,
        email: form.email,
        role: form.role,
      })
      ElMessage.success(t('common.createSuccess'))
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to submit:', error)
  } finally {
    submitLoading.value = false
  }
}

const handleResetPassword = async () => {
  const valid = await resetFormRef.value.validate().catch(() => false)
  if (!valid) return

  resetLoading.value = true
  try {
    await resetPassword(currentUser.value.id, { password: resetForm.password })
    ElMessage.success('密码重置成功')
    resetPasswordVisible.value = false
  } catch (error) {
    console.error('Failed to reset password:', error)
  } finally {
    resetLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(t('user.deleteConfirm', { name: row.username }), t('common.confirm'), { type: 'warning' })
    await deleteUser(row.id)
    ElMessage.success(t('common.deleteSuccess'))
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete:', error)
    }
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.header-filters {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
